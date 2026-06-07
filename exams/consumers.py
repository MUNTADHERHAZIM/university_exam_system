import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ExamAttempt, ChatMessage, ViolationLog, ProctorSnapshot

class ExamProctorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.attempt_id = self.scope['url_route']['kwargs']['attempt_id']
        self.attempt = await self.get_attempt()
        self.exam_id = self.attempt.exam_id
        
        self.room_group_name = f'proct_attempt_{self.attempt_id}'
        self.exam_group_name = f'exam_monitor_{self.exam_id}'

        # Join both groups
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.exam_group_name, self.channel_name)
        
        await self.accept()

    @database_sync_to_async
    def get_attempt(self):
        return ExamAttempt.objects.select_related('exam').get(pk=self.attempt_id)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_discard(self.exam_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'violation':
            v_type = data.get('type')
            details = data.get('details', '')
            # Save to DB
            await self.save_violation(v_type, details)
            # Broadcast to BOTH groups (student-specific and exam-wide)
            payload = {
                'type': 'proctor_notification',
                'attempt_id': self.attempt_id,
                'student_name': self.attempt.student.get_full_name(),
                'message': f'تم رصد مخالفة: {v_type}',
                'details': details,
                'timestamp': timezone.now().strftime('%H:%M:%S'),
                'violation_type': v_type
            }
            await self.channel_layer.group_send(self.room_group_name, payload)
            await self.channel_layer.group_send(self.exam_group_name, payload)

    async def proctor_notification(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_violation(self, v_type, details):
        attempt = ExamAttempt.objects.get(id=self.attempt_id)
        ViolationLog.objects.create(
            attempt=attempt,
            violation_type=v_type,
            details=details[:255]
        )
        attempt.violations_count += 1
        attempt.save(update_fields=['violations_count'])


class ExamMonitorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.exam_id = self.scope['url_route']['kwargs']['exam_id']
        self.room_group_name = f'exam_monitor_{self.exam_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def proctor_notification(self, event):
        # Forward updates to the proctor dashboard
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_violation(self, v_type, details):
        attempt = ExamAttempt.objects.get(id=self.attempt_id)
        ViolationLog.objects.create(
            attempt=attempt,
            violation_type=v_type,
            details=details[:255]
        )
        attempt.violations_count += 1
        attempt.save(update_fields=['violations_count'])


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.attempt_id = self.scope['url_route']['kwargs']['attempt_id']
        self.room_group_name = f'chat_attempt_{self.attempt_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        sender_id = self.scope['user'].id

        # Save to DB
        msg_obj = await self.save_message(message)

        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.scope['user'].username,
                'is_me': True, # Logic will handle this on frontend
                'timestamp': msg_obj.timestamp.strftime('%H:%M'),
                'sender_id': sender_id
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, message):
        attempt = ExamAttempt.objects.get(id=self.attempt_id)
        return ChatMessage.objects.create(
            attempt=attempt,
            sender=self.scope['user'],
            message=message
        )
