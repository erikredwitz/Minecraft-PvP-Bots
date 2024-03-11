import math
import sys
import threading
import time

from javascript import require, On

mineflayer = require('mineflayer')
pathfinder_plugin = require('mineflayer-pathfinder')
pvp = require('mineflayer-pvp').plugin
statemachinePluginDict = require("mineflayer-statemachine")
pathfinder = pathfinder_plugin.pathfinder
Movements = pathfinder.Movements
goals = pathfinder.goals
v = require('vec3')
StateTransition = statemachinePluginDict.StateTransition
BotStateMachine = statemachinePluginDict.BotStateMachine
EntityFilters = statemachinePluginDict.EntityFilters
BehaviorFollowEntity = statemachinePluginDict.BehaviorFollowEntity
BehaviorLookAtEntity = statemachinePluginDict.BehaviorLookAtEntity
BehaviorGetClosestEntity = statemachinePluginDict.BehaviorGetClosestEntity
NestedStateMachine = statemachinePluginDict.NestedStateMachine
StateBehaviour = statemachinePluginDict.StateBehaviour
AttackState =

RANGE_GOAL = 1
BOT_USERNAME = 'python'

bot = mineflayer.createBot({
    'host': '127.0.0.1',
    'port': sys.argv[1],
    'username': BOT_USERNAME
})

bot.loadPlugin(pathfinder_plugin.pathfinder)
bot.loadPlugin(pvp)
print("Started mineflayer")

target_entity = None
target_mode = False
thread = None

half_player_width = 0.3

hitbox_height = 1.8

eye_height = 1.6


def getAttackLookPosition(target_entity):
    target_position = target_entity['position']
    if target_entity.type != 'player':
        return target_position
    else:
        look_x = 0
        look_y = 0
        look_z = 0
        bot_position = bot.entity.position
        x_difference = target_position.x - bot_position.x
        y_difference = target_position.y - bot_position.y
        z_difference = target_position.z - bot_position.z
        if y_difference < eye_height:
            look_y = target_position.y + hitbox_height
        elif y_difference > hitbox_height - eye_height:
            look_y = target_position.y
        else:
            look_y = bot_position.y + eye_height

        if x_difference < half_player_width:
            look_x = target_position.x - half_player_width
        elif x_difference > half_player_width:
            look_x = target_position.x + half_player_width
        else:
            look_x = bot_position.x

        if z_difference < half_player_width:
            look_z = target_position.z - half_player_width
        elif z_difference > half_player_width:
            look_z = target_position.z + half_player_width
        else:
            look_z = bot_position.z
        return v(look_x, look_y, look_z)


def face(target_entity):
    position = getAttackLookPosition(target_entity)
    bot.lookAt(position, [True])


@On(bot, 'spawn')
def handle(*args):
    print("I spawned 👋")
    movements = pathfinder.Movements(bot)

    @On(bot, 'chat')
    def handle_msg(this, sender, message, *args):
        if message == 'fight':
            global target_entity
            target_entity = bot.players[sender].entity
            startAttack()
            print("Attacke gestartet")
        elif message == 'stop':
            global target_mode
            target_mode = False
            print("stop")

    @On(bot, 'entityHurt')
    def handle_entity_hurt(this, entity):
        print(entity.id)
        print(bot.entity.id)
        if entity.id == bot.entity.id:
            global target_entity
            target_entity = bot.nearestEntity()
            startAttack()

    def printHitDistance():
        return str(getDistance(bot.entity.position, bot.nearestEntity().position))


@On(bot, "end")
def handle(*args):
    print("Bot ended!", args)


def getDistance(tdv1, tdv2):
    x = tdv1.x - tdv2.x
    y = tdv1.y - tdv2.y
    z = tdv1.z - tdv2.z
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


def getLength(three_dim_vector):
    return math.sqrt(three_dim_vector.x ** 2 + three_dim_vector.y ** 2 + three_dim_vector.z ** 2)


def punch():
    entity = bot.entityAtCursor(3.5)
    if entity is None:
        bot.swingArm()
    else:
        bot.attack(entity)


def attackCycle():
    global target_mode
    target_mode = True
    global target_entity
    while target_mode:
        global target_entity
        face(target_entity)
        punch()
        time.sleep(0.05)


def startAttack():
    global target_mode
    if target_mode:
        return
    global thread
    thread = threading.Thread(target=attackCycle())
    thread.start()
    return


# Define the state class
class AttackState(StateBehaviour):
    def __init__(self, bot):
        self.bot = bot
        self.active = False
        self.state_name = 'AttackState'

    def on_state_entered(self):
        print(f"{self.bot.username} has entered the {self.state_name} state.")
        attackCycle()


    def on_state_exited(self):
        print(f"{self.bot.username} has left the {self.state_name} state.")






