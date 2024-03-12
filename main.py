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


def startDiggingIfCan(bot):
    block_at_cursor = bot.blockAtCursor
    if bot.canDig(block_at_cursor):
        bot.dig(block_at_cursor, 'ignore')


def getDistance(tdv1, tdv2):
    x = tdv1.x - tdv2.x
    y = tdv1.y - tdv2.y
    z = tdv1.z - tdv2.z
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


def getLength(three_dim_vector):
    return math.sqrt(three_dim_vector.x ** 2 + three_dim_vector.y ** 2 + three_dim_vector.z ** 2)


class DuelBot:
    duelBotList = []

    def __init__(self, name):
        self.bot = mineflayer.createBot({
            'host': '127.0.0.1',
            'port': sys.argv[1],
            'username': name
        })
        self.target_entity = None
        self.target_mode = False
        self.thread = None
        self.duelBotList.append(self)
        self.botTargetIndex = -1

        @On(self.bot, 'spawn')
        def handle(*args):
            print("I spawned 👋")
            self.endAttack()

        @On(self.bot, 'chat')
        def handle_msg(this, sender, message, *args):
            if message == 'fight':
                self_index = self.duelBotList.index(self)
                opponent_index = 0
                if self_index % 2 == 0:
                    opponent_index = self_index + 1
                else:
                    opponent_index = self_index - 1
                if len(self.duelBotList) > opponent_index:
                    self.target_entity = self.duelBotList[opponent_index].bot.entity
                    self.botTargetIndex = opponent_index
                    self.startAttack()
            elif message == 'stop':
                self.endAttack()

        @On(self.bot, 'entityHurt')
        def handle_entity_hurt(this, entity):
            if entity.id == self.bot.entity.id:
                self.target_entity = self.bot.nearestEntity()
                self.startAttack()

        @On(self.bot, 'entitySpawn')
        def handle_entity_dead(this, entity):
            if not self.target_mode:
                return
            if entity.id == self.target_entity.id:
                self.endAttack()

        @On(self.bot, "end")
        def handle(*args):
            print("Bot ended!", args)

    def getAttackLookPosition(self, target_entity):
        half_player_width = 0.3
        hitbox_height = 1.8
        eye_height = 1.6
        target_position = target_entity['position']
        if target_entity.type != 'player':
            return target_position
        else:
            look_x = 0
            look_y = 0
            look_z = 0
            bot_position = self.bot.entity.position
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

    def face(self, target_entity):
        position = self.getAttackLookPosition(target_entity)
        self.bot.lookAt(position, True)

    def endAttack(self):
        print("endAttack")
        self.target_mode = False
        self.bot.setControlState('forward', False)
        self.bot.setControlState('sprint', False)
        if 0 <= self.botTargetIndex < len(self.duelBotList):
            target_bot = self.duelBotList[self.botTargetIndex]
            if target_bot.target_mode:
                target_bot.endAttack()
            self.botTargetIndex = -1

    def printHitDistance(self):
        return str(getDistance(self.bot.entity.position, self.bot.nearestEntity().position))

    def punch(self):
        entity = self.bot.entityAtCursor(3.5)
        if entity is None:
            self.bot.swingArm()
        else:
            self.bot.attack(entity)

    def attackCycle(self):
        while self.target_mode and self.bot.entities[self.target_entity.id] is not None:
            self.face(self.target_entity)
            self.punch()
            time.sleep(0.05)
        if self.target_mode:
            self.endAttack()

    def startAttack(self):
        if self.target_mode:
            return
        self.target_mode = True
        self.bot.setControlState('forward', True)
        self.bot.setControlState('sprint', True)
        self.thread = threading.Thread(target=self.attackCycle)
        self.thread.start()

    def targetMode(self, target_mode):
        self.target_mode = target_mode


print("Started mineflayer")
bot1 = DuelBot(name="pyt")
bot2 = DuelBot(name="hon")
