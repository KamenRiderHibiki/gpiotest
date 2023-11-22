# -*- coding:utf-8 -*-
from __future__ import print_function
import RPi.GPIO as GPIO  # 引入包
import time
import atexit
from evdev import InputDevice
from select import select

GPIO.setmode(GPIO.BOARD)  # 设置为BOARD模式

atexit.register(GPIO.cleanup)

# 控制L298N
a1, a2, b1, b2 = 11, 12, 13, 15
GPIO.setup(a1, GPIO.OUT, initial=False)  # 设置物理11引脚为输出引脚
GPIO.setup(a2, GPIO.OUT, initial=False)
GPIO.setup(b1, GPIO.OUT, initial=False)
GPIO.setup(b2, GPIO.OUT, initial=False)
pwm_a = GPIO.PWM(a1, 20)
pwm_b = GPIO.PWM(b1, 20)
pwm_ar = GPIO.PWM(a2, 20)
pwm_br = GPIO.PWM(b2, 20)


def forward(i=100):
    """按百分比前进"""
    i = (i // 5 + 1) * 5
    if i > 100:
        i = 100
    pwm_a.start(i)
    pwm_b.start(i)
    pwm_ar.stop()
    pwm_br.stop()
    # GPIO.output(a1, GPIO.HIGH)  # 设置11为高电平
    # GPIO.output(b1, GPIO.HIGH)


def retreat(i=100):
    """按百分比后退"""
    i = (i // 5 + 1) * 5
    if i > 100:
        i = 100
    pwm_ar.start(i)
    pwm_br.start(i)
    pwm_a.stop()
    pwm_b.stop()


def left(i=1):
    """左转"""
    if i == 0:
        pwm_a.stop()
        pwm_ar.stop()
        pwm_br.stop()
        pwm_b.start(100)
    else:
        pwm_a.stop()
        pwm_ar.start(100)
        pwm_br.stop()
        pwm_b.start(100)


def right(i=1):
    """右转"""
    if i == 0:
        pwm_b.stop()
        pwm_ar.stop()
        pwm_br.stop()
        pwm_a.start(100)
    else:
        pwm_a.start(100)
        pwm_ar.stop()
        pwm_b.stop()
        pwm_br.start(100)


def stop():
    """停止小车的动作"""
    pwm_a.stop()
    pwm_b.stop()
    pwm_ar.stop()
    pwm_br.stop()


# 超声波
uc1o, uc1i, uc2o, uc2i = 16, 18, 22, 29
GPIO.setup(uc1o, GPIO.OUT, initial=False)
GPIO.setup(uc1i, GPIO.IN)
GPIO.setup(uc2o, GPIO.OUT, initial=False)
GPIO.setup(uc2i, GPIO.IN)


def check_dist(i=0):
    """超声波测距"""
    if 0 == i:
        GPIO.output(uc1o, GPIO.HIGH)
        time.sleep(0.00015)
        GPIO.output(uc1o, GPIO.LOW)
        while not GPIO.input(uc1i):
            pass
        t1 = time.time()
        while GPIO.input(uc1i):
            pass
        t2 = time.time()
        dist = (t2 - t1) * 340 * 100 / 2
        print(dist, end='')
        print('cm')
        return dist
    if 1 == i:
        GPIO.output(uc2o, GPIO.HIGH)
        time.sleep(0.00015)
        GPIO.output(uc2o, GPIO.LOW)
        while not GPIO.input(uc2i):
            pass
        t1 = time.time()
        while GPIO.input(uc2i):
            pass
        t2 = time.time()
        dist = (t2 - t1) * 340 * 100 / 2
        print(dist, end='')
        print('cm')
        return dist
    else:
        print("No such sensor!")


# 红外避障
ar1, ar2, ar3, ar4, ar5 = 31, 33, 35, 37, 7
GPIO.setup(ar1, GPIO.IN)  # 右侧
GPIO.setup(ar2, GPIO.IN)  # 右前
GPIO.setup(ar3, GPIO.IN)  # 左前
GPIO.setup(ar4, GPIO.IN)  # 左侧
GPIO.setup(ar5, GPIO.IN)  # 后侧


def suspend(i=0):
    """红外线避障，检查小车是否到达悬崖或障碍"""  # 高电平无障碍，低有障碍
    if 0 == i:
        status = not GPIO.input(ar1) and GPIO.input(ar2) and GPIO.input(ar3) and not GPIO.input(ar4) and GPIO.input(ar5)
        return status
    if 1 == i:
        status = GPIO.input(ar1)
        return status
    if 2 == i:
        status = GPIO.input(ar2)
        return status
    if 3 == i:
        status = GPIO.input(ar3)
        return status
    if 4 == i:
        status = GPIO.input(ar4)
        return status
    if 5 == i:
        status = GPIO.input(ar5)
        return status


# 舵机
sg90 = 32
GPIO.setup(sg90, GPIO.OUT, initial=False)
steer = GPIO.PWM(sg90, 50)  # 50HZ
print("Init finish")


def move_arc(arc=90):
    """转动相应角度"""
    steer.start(0)
    arc = arc % 180
    steer.ChangeDutyCycle(2.5 + 10 * arc / 180)
    time.sleep(0.2)
    steer.ChangeDutyCycle(0)


def end():
    """清除引脚设置"""
    GPIO.cleanup()  # 清除本程序中的引脚设置，释放资源


class State:
    trap = False
    Turn_left = False
    Turn_right = False
    Fall_risk = False


state = State()


def auto_pilot():
    """自动驾驶"""
    stop()
    if state.Fall_risk:
        rf = suspend(2)  # type: Union[bool, Any]
        lf = suspend(3)
        back = suspend(5)
        if rf and lf and back:  # 全悬空
            stop()
        elif rf:  # 右前悬空
            if lf:  # 前边悬空
                retreat()
            else:
                left()  # 左边触地
        elif lf:  # 右前触地左前悬空
            right()
        elif back:  # 后边悬空
            if state.trap:
                stop()
            else:
                forward()
        else:  # 没事了
            state.Fall_risk = False
        return
    rf = suspend(2)  # type: Union[bool, Any]
    lf = suspend(3)
    back = suspend(5)
    if rf or lf or back:
        state.Fall_risk = True
        return
    if state.Turn_left:  # 左转避障状态
        if suspend(1):  # 右侧无障碍恢复正常状态
            print("准备前进")
            state.trap = False
            state.Turn_left = False
            state.Turn_right = False
        else:  # 继续避障
            print("左转向")
            left()
    if state.Turn_right:  # 右转避障状态
        if suspend(4):
            print("准备前进")
            state.trap = False
            state.Turn_left = False
            state.Turn_right = False
        else:
            print("右转向")
            right()
    if state.trap:  # 在陷阱状态
        print("陷阱状态")
        obstacle_left = suspend(4)
        obstacle_right = suspend(1)
        if not obstacle_left and not obstacle_right:  # 左右均有障碍
            if check_dist(1) < 10.0:
                print("无路走")
                stop()
            else:
                print("倒车")
                retreat()
        elif obstacle_left:  # 左边没障碍
            print("开始左转向")
            state.trap = False
            state.Turn_left = True
            state.Turn_right = False
            left()
        elif obstacle_right:
            print("开始右转向")
            state.trap = False
            state.Turn_left = False
            state.Turn_right = True
            right()
    else:  # 没有异常flag
        distance_f = 0
        distance_f = check_dist(0)
        while not distance_f:
            pass
        if distance_f > 20.0:
            print("前进")
            forward()
        else:
            obstacle_left = suspend(4)
            obstacle_right = suspend(1)
            if obstacle_left:
                if obstacle_right:
                    print("后退")
                    retreat()
                else:
                    print("避障左转向")
                    left()
            else:
                if obstacle_right:
                    print("避障右转向")
                    right()
                else:  # 左右均有障碍
                    state.trap = True
                    print("进入陷阱")


if __name__ == '__main__':
    dev = InputDevice('/dev/input/event0')
    if dev <= 0:
        print("open /dev/input/event0 device error!")
        end()
        quit(1)
    running = True
    auto_mode = False
    while running:
        if auto_mode:
            auto_pilot()
        select([dev], [], [])
        for event in dev.read():
            if (event.value == 1 or event.value == 0) and event.code != 0:
                if 17 == event.code:
                    if event.value:
                        print("Forward")
                        forward()
                    else:
                        print("stop")
                        stop()
                if 31 == event.code:
                    if event.value:
                        print("Reverse")
                        retreat()
                    else:
                        print("Stop")
                        stop()
                if 30 == event.code:
                    if event.value:
                        print("Turn left")
                        left(1)
                    else:
                        print("stop")
                        stop()
                if 32 == event.code:
                    if event.value:
                        print("Turn right")
                        right(1)
                    else:
                        print("Stop")
                        stop()
                if 1 == event.code:
                    running = False
                    break
                if 33 == event.code:
                    if event.value == 1:
                        print("AutoChange")
                        auto_mode = not auto_mode
                        if not auto_mode:
                            stop()
    end()
    quit(0)
