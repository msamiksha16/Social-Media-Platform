# core/consumers.py
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import json

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Import here instead of top-level
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'notifications_{self.user_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        print(f"{self.scope['user'].username} connected to {self.group_name}")
        logger.info(f"{self.scope['user'].username} connected to {self.group_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print(f"{self.scope['user'].username} disconnected from {self.group_name}")
        logger.info(f"{self.scope['user'].username} disconnected from {self.group_name}")

    async def send_notification(self, event):
        print("Notification received by consumer:", event)  # This prints to terminal
        await self.send(text_data=json.dumps({
            'text': event['text']
        }))

