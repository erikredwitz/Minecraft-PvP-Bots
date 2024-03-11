import math

from javascript import require, On

mineflayer = require('mineflayer')
pathfinder_plugin = require('mineflayer-pathfinder')
pvp = require('mineflayer-pvp').plugin
pathfinder = pathfinder_plugin.pathfinder
Movements = pathfinder.Movements
goals = pathfinder.goals

RANGE_GOAL = 1
BOT_USERNAME = 'python'

bot = mineflayer.createBot({
    'host': '127.0.0.1',
    'port': 64029,
    'username': BOT_USERNAME
})

bot.loadPlugin(pathfinder_plugin.pathfinder)
bot.loadPlugin(pvp)
print("Started mineflayer")


@On(bot, 'spawn')
def handle(*args):
    print("I spawned 👋")
    movements = pathfinder.Movements(bot)

    @On(bot, 'chat')
    def handle_msg(this, sender, message, *args):
        if message == 'fight':
            # print(bot.players[sender].entity.id)
            entity = bot.entities[bot.players[sender].entity.id]
            # bot.attack(entity)
            bot.pvp.attack(entity)
        if message == 'stop':
            bot.pvp.stop()

    @On(bot, 'entityHurt')
    def handle_entity_hurt(this, entity):
        distance = bot.entity.position.minus(entity.position)
        print(str(getLength(distance)))
        # bot.chat(distance)


@On(bot, "end")
def handle(*args):
    print("Bot ended!", args)


def getLength(three_dim_vector):
    return math.sqrt(three_dim_vector.x ** 2 + three_dim_vector.y ** 2 + three_dim_vector.z ** 2)


def punch():
    entity = bot.entityAtCursor(maxDistance=3.0)
    if entity is None:
        return
    bot.attack(entity)



