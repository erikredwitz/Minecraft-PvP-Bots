import math
import sys
import threading
import time
import random

from javascript import require, On

mineflayer = require('mineflayer')
pathfinder_plugin = require('mineflayer-pathfinder')
pvp = require('mineflayer-pvp').plugin
pathfinder = pathfinder_plugin.pathfinder
Movements = pathfinder.Movements
goals = pathfinder.goals
v = require('vec3')


class ActionState:

    def __init__(self, init_vector):
        self.walk_forwards, self.walk_left, self.walk_backwards, self.walk_right, self.jump, self.sneak, \
            self.sprint, self.facing_yaw_change, self.facing_pitch_change, self.left_click, self.old_left_click, \
            self.right_click, self.old_right_click, self.slot, self.old_slot = init_vector

    def change_state(self, new_state):
        self.old_right_click = self.right_click
        self.old_left_click = self.left_click
        self.old_slot = self.slot
        self.walk_forwards, self.walk_left, self.walk_backwards, self.walk_right, self.jump, self.sneak, \
            self.sprint, self.facing_yaw_change, self.facing_pitch_change, self.left_click, \
            self.right_click, self.slot = new_state

    def execute_time_step(self, bot):
        bot.setControlState('forward', self.walk_forwards)
        bot.setControlState('left', self.walk_left)
        bot.setControlState('backward', self.walk_backwards)
        bot.setControlState('right', self.walk_right)
        bot.setControlState('jump', self.jump)
        bot.setControlState('sneak', self.sneak)
        bot.setControlState('sprint', self.sprint)
        new_yaw = bot.entity.yaw + self.facing_yaw_change
        new_pitch = bot.entity.pitch + self.facing_pitch_change
        bot.look(new_yaw, new_pitch)
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


class EnvironmentState:
    def __init__(self, init_vector):
        self.my_x, self.my_y, self.my_z, self.my_yaw, self.my_pitch, \
            self.opponent_x, self.opponent_y, self.opponent_z, self.opponent_yaw, self.opponent_pitch = init_vector


def startDiggingIfCan(bot):
    block_at_cursor = bot.blockAtCursor
    if bot.canDig(block_at_cursor):
        bot.dig(block_at_cursor, 'ignore')


def getDistance(tdv1, tdv2):
    x = tdv1.x - tdv2.x
    y = tdv1.y - tdv2.y
    z = tdv1.z - tdv2.z
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


def getDifference(tdv1, tdv2):
    x = tdv1.x - tdv2.x
    y = tdv1.y - tdv2.y
    z = tdv1.z - tdv2.z
    return v(x, y, z)


def sumVec(tdv1, tdv2):
    x = tdv1.x + tdv2.x
    y = tdv1.y + tdv2.y
    z = tdv1.z + tdv2.z
    return v(x, y, z)


def getLength(three_dim_vector):
    return math.sqrt(three_dim_vector.x ** 2 + three_dim_vector.y ** 2 + three_dim_vector.z ** 2)


def isVecZero(vec):
    return vec.x == 0, vec.y == 0, vec.z == 0


class DuelBot:
    duelBotList = []

    def __init__(self, name, attack_time):
        self.bot = mineflayer.createBot({
            'host': '127.0.0.1',
            'port': sys.argv[1],
            'username': name
        })
        self.target_entity = None
        self.target_mode = False
        self.duelBotList.append(self)
        self.botTargetIndex = -1
        self.attackTime = attack_time
        self.last_hit = False
        self.wtap = False
        self.target_last_position = None

        @On(self.bot, 'spawn')
        def handle(*args):
            print(self.bot.username + " spawned")
            self.endAttack()
            print(self.bot.entity.position)

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
                self.last_hit = False
                if not self.target_mode:
                    self.target_entity = self.bot.nearestEntity()
                    self.startAttack()
            elif self.target_mode and self.target_entity is not None:
                if entity.id == self.target_entity.id:
                    self.last_hit = True
                    self.bot.setControlState('forward', False)
                    self.bot.setControlState('sprint', False)
                    self.bot.setControlState('forward', True)
                    self.bot.setControlState('sprint', True)
                    if not self.bot.getControlState('right'):
                        self.bot.setControlState('right', True)
                        self.bot.setControlState('left', False)
                    else:
                        self.bot.setControlState('right', False)
                        self.bot.setControlState('left', True)

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

            if z_difference < -half_player_width:
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
        self.bot.setControlState('left', False)
        self.bot.setControlState('right', False)
        self.bot.setControlState('jump', False)
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
            distance = getDistance(self.target_entity['position'], self.bot.entity['position'])
            target_velocity = v(0, 0, 0)
            if self.target_last_position is not None:
                target_velocity = getDifference(self.target_entity['position'], self.target_last_position)
            target_move_distance = getDistance(sumVec(self.target_entity['position'], target_velocity),
                                               self.bot.entity['position'])
            self_move_distance = getDistance(self.target_entity['position'],
                                             sumVec(self.bot.entity['position'], self.bot.entity['velocity']))
            target_move_distance_change = target_move_distance - distance
            self_move_distance_change = self_move_distance - distance
            self.target_last_position = self.target_entity['position']
            if distance > 8:
                self.bot.setControlState('jump', True)
                self.bot.setControlState('left', False)
                self.bot.setControlState('right', False)
            elif self.last_hit and self_move_distance_change <= 0.05 \
                    and distance < 4:
                self.bot.setControlState('forward', False)
                self.bot.setControlState('left', False)
                self.bot.setControlState('right', False)
                self.bot.setControlState('jump', False)
                self.wtap = True
            else:
                if not self.last_hit or distance > 6:
                    self.wtap = False
                self.bot.setControlState('jump', False)
                self.bot.setControlState('forward', True)
                if not (self.wtap or self.bot.getControlState('left') or self.bot.getControlState('right')):
                    if random.randint(0, 1) == 1:
                        self.bot.setControlState('left', True)
                    else:
                        self.bot.setControlState('right', True)
            if self.attackTime > 0:
                time.sleep(self.attackTime)
        self.endAttack()

    def startAttack(self):
        if self.target_mode:
            return
        self.target_mode = True
        self.bot.setControlState('right', True)
        self.bot.setControlState('forward', True)
        self.bot.setControlState('sprint', True)
        print('target')
        print(self.target_entity['position'])
        thread = threading.Thread(target=self.attackCycle)
        thread.start()

    def targetMode(self, target_mode):
        self.target_mode = target_mode


print("Started mineflayer")
bot1 = DuelBot(name="pyt", attack_time=0.05)
bot2 = DuelBot(name="hon", attack_time=0.2)
