import math
import sys
import threading
import time

from javascript import require, On

mineflayer = require('mineflayer')
pathfinder_plugin = require('mineflayer-pathfinder')
pvp = require('mineflayer-pvp').plugin
pathfinder = pathfinder_plugin.pathfinder
Movements = pathfinder.Movements
goals = pathfinder.goals
v = require('vec3')

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
        if y_difference < eye_height - hitbox_height:
            look_y = target_position.y + hitbox_height
        elif y_difference > eye_height:
            look_y = target_position.y
        else:
            look_y = bot_position.y + eye_height

        if x_difference < -half_player_width:
            look_x = target_position.x + half_player_width
        elif x_difference > half_player_width:
            look_x = target_position.x - half_player_width
        else:
            look_x = bot_position.x

        if z_difference < -2 * half_player_width:
            look_z = target_position.z + half_player_width
        elif z_difference > half_player_width:
            look_z = target_position.z - half_player_width
        else:
            look_z = bot_position.z
        return v(look_x, look_y, look_z)


def face(target_entity):
    position = getAttackLookPosition(target_entity)
    bot.lookAt(position, True)


def endAttack():
    print("endAttack")
    global target_mode
    global bot
    target_mode = False
    bot.setControlState('forward', False)
    bot.setControlState('sprint', False)


@On(bot, 'spawn')
def handle(*args):
    global target_mode
    print("I spawned 👋")
    movements = pathfinder.Movements(bot)
    endAttack()


@On(bot, 'chat')
def handle_msg(this, sender, message, *args):
    global target_entity
    global target_mode
    if message == 'fight':
        target_entity = bot.players[sender].entity
        startAttack()
    elif message == 'stop':
        endAttack()


@On(bot, 'entityHurt')
def handle_entity_hurt(this, entity):
    global target_entity
    if entity.id == bot.entity.id:
        target_entity = bot.nearestEntity()
        startAttack()


@On(bot, 'entityDeath')
def handle_entity_dead(this, entity):
    global target_entity
    print(target_entity.id)
    print(entity.id)
    if entity.id == target_entity.id:
        endAttack()


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
    global target_entity
    while target_mode and bot.entities[target_entity.id] is not None:
        face(target_entity)
        punch()
        time.sleep(0.05)
    if target_mode:
        endAttack()


def startAttack():
    global target_mode
    global thread
    if target_mode:
        return
    target_mode = True
    bot.setControlState('forward', True)
    bot.setControlState('sprint', True)
    thread = threading.Thread(target=attackCycle)
    thread.start()


def startDiggingIfCan(bot):
    block_at_cursor = bot.blockAtCursor
    if bot.canDig(block_at_cursor):
        bot.dig(block_at_cursor, 'ignore')


class ActionState:
    walk_forwards = False
    walk_left = False
    walk_backwards = False
    walk_right = False
    jump = False
    sneak = False
    sprint = False
    facing_yaw_change = 0.0
    facing_pitch_change = 0.0
    left_click = False
    old_left_click = False
    right_click = False
    old_right_click = False
    slot = 0
    old_slot = 0

    def executeTimeStep(self, bot):
        bot.setControlState('forward', self.walk_forwards)
        bot.setControlState('left', self.walk_left)
        bot.setControlState('backward', self.walk_backwards)
        bot.setControlState('right', self.walk_right)
        bot.setControlState('jump', self.jump)
        bot.setControlState('sneak', self.sneak)
        bot.setControlState('sprint', self.sprint)
        yaw_change = bot.entity.yaw + self.facing_yaw_change
        pitch_change = bot.entity.pitch + self.facing_pitch_change
        bot.look(yaw_change, pitch_change)
        bot.setQuickBarSlot(self.slot)
        if self.left_click:
            bot.swingArm()
            if not self.old_left_click:
                self.old_left_click = True
                entity = bot.entityAtCursor(3.5)
                if entity is not None:
                    bot.attack(entity, False)
                else:
                    startDiggingIfCan(bot)
            else:
                if bot.targetDigBlock is not None:
                    bot.stopDigging()
                bot.startDiggingIfCan(bot)
        else:
            if self.old_left_click:
                self.old_left_click = False
                if bot.targetDigBlock is not None:
                    bot.stopDigging()
        if self.right_click:
            if not self.old_right_click:
                self.old_right_click = True
                bot.activateItem()
            elif self.old_slot != self.slot:
                bot.activateItem()
        else:
            if self.old_right_click:
                self.old_right_click = False
                if self.old_slot == self.slot:
                    bot.deactivateItem()
