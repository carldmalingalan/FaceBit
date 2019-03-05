from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from .models import MonitorLog, DataSets
from .apps import train_datasets

import asyncio
import json


class TrainData(AsyncConsumer):
	async def websocket_connect(self, event):
		await self.send({'type':'websocket.accept'})
		
		await self.channel_layer.group_add('training', self.channel_name)
		

	async def websocket_receive(self, event):
		pass
		# status = json.loads(event['text'])
		# if status['status'] == 'train':
		# 	await self.start_training()
		

	async def websocket_disconnect(self, event):
		print("Disconnected ", event)

	async def websocket_error(self, event):
		print("Error", event)

	async def training_status(self, event):
		await self.send({
			'type':'websocket.send',
			'text':json.dumps(event['log_data']),
			})


class LogConsumer(AsyncConsumer):
	async def websocket_connect(self, event):
		# print("Connected ", event)
		
		await self.send({
			'type': 'websocket.accept',
			})
		

		await self.channel_layer.group_add('logStatus', self.channel_name)

	async def logStatus_newEntry(self, event):
		await self.send({
			'type': 'websocket.send',
			'text': json.dumps(event),
			})

	async def websocket_receive(self, event):
		print("Receive ", event)

	async def websocket_disconnect(self, event):
		print("Disconnected ", event)

	async def websocket_error(self, event):
		print("Error", event)

	@database_sync_to_async
	def get_init_five(self):
		return MonitorLog.log_info_batch()



