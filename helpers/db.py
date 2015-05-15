from pymongo import MongoClient

client = MongoClient('localhost')
mongo = client.waapi
mongo.authenticate('waapi', 'adventuretime')

Lines = mongo.lines
Chats = mongo.chats
Avatars = mongo.avatars
Logs = mongo.logs
Users = mongo.users
