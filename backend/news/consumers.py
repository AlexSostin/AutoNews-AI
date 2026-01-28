import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GenerationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time article generation progress.
    """
    
    async def connect(self):
        """Accept WebSocket connection and join task group"""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.group_name = f"generation_{self.task_id}"
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"✓ WebSocket connected for task: {self.task_id}")
    
    async def disconnect(self, close_code):
        """Handle disconnection"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print(f"✗ WebSocket disconnected: {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming messages (not used for now)"""
        pass
    
    async def send_progress(self, event):
        """Send progress update to client"""
        await self.send(text_data=json.dumps({
            'step': event['step'],
            'progress': event['progress'],
            'message': event['message']
        }))
