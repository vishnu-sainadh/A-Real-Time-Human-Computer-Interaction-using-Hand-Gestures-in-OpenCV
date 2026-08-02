import os
import time
from datetime import datetime

import autopy
import cv2
import cvzone
import numpy as np
import pyautogui
import screen_brightness_control as sbc
from AppOpener import run
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Controller as MouseController

import HandTrackingModule2 as HTM2

##########################
wCam, hCam = 640, 480
wScr, hScr = autopy.screen.size()

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

cap.set(3, wCam)
cap.set(4, hCam)

pyautogui.FAILSAFE = False

prev_frame = None

buttonPressed = False
buttonCounter = 0
buttonDelay = 5

keyboard = KeyboardController()
mouse = MouseController()

#run('ls')

capslock_boolean = False

pTime = 0


#########################

class Button():
    def __init__(self, pos, text, size=[85, 85]):
        self.pos = pos
        self.size = size
        self.text = text


def drawKeyBoard(img, buttonList):
    imgNew = np.zeros_like(img, np.uint8)
    for button in buttonList:
        x, y = button.pos
        cvzone.cornerRect(imgNew, (button.pos[0], button.pos[1], button.size[0], button.size[1]),
                          20, rt=0)
        cv2.rectangle(imgNew, button.pos, (x + button.size[0], y + button.size[1]),
                      (255, 0, 255), cv2.FILLED)
        cv2.putText(imgNew, button.text, (x + 40, y + 60),
                    cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 3)
    out = img.copy()
    alpha = 0
    mask = imgNew.astype(bool)
    out[mask] = cv2.addWeighted(img, alpha, imgNew, 1 - alpha, 0)[mask]
    return out


keys = [["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", ","],
        ["Z", "X", "C", "V", "B", "N", "M", "."]]

buttonList = []
for i in range(len(keys)):
    for j, key in enumerate(keys[i]):
        buttonList.append(Button([100 * j + 150, 100 * i + 75], key))

buttonList.append(Button([100 * 8 + 150, 100 * 3 + 75], "<--", [185, 85]))
buttonList.append(Button([150, 100 * 4 + 75], "CAPS", [185, 85]))
buttonList.append(Button([350, 100 * 4 + 75], "SPACE", [485, 85]))
buttonList.append(Button([850, 100 * 4 + 75], "ENTER", [285, 85]))


def set_KeyBoard():
    cap.set(3, 1280)
    cap.set(4, 720)


def set_Mouse():
    cap.set(3, 640)
    cap.set(4, 480)


class GestureController:

    def __init__(self):
        self.frameR = 150  # Frame Reduction
        self.smoothening = 7  # Mouse Damping Factor
        self.plocX, self.plocY = 0, 0

        self.vk, self.bk, self.sk = 1, 1, 1
        self.volume_change_factor, self.brightness_change_factor, self.scroll_change_factor = 1, 10, 150

        self.prev_dynamic_x, self.prev_dynamic_y, self.dynamic_frames = None, None, 0

        self.keyboard_mode = False

    def action_listener(self, button_is_pressed, previous_frame, text_x_cood=20, text_y_cood=100, butDelay=5):
        global buttonPressed, buttonDelay, prev_frame
        buttonPressed = button_is_pressed
        buttonDelay = butDelay
        prev_frame = previous_frame
        if prev_frame.startswith('Scroll') == False:
            self.dynamic_init()
        cv2.putText(img, previous_frame, (text_x_cood, text_y_cood), cv2.FONT_HERSHEY_PLAIN, 3, (255, 255, 0), 3)

    def dynamic_init(self):
        self.prev_dynamic_x, self.prev_dynamic_y, self.dynamic_frames = None, None, 0

    def dynamic_distance(self, x, y):
        dx = (self.prev_dynamic_x - x) * 10
        dy = (self.prev_dynamic_y - y) * 10
        sx = 1 if dx > 0 else -1
        sy = 1 if dy > 0 else -1
        return dx, dy, sx, sy

    def change_factor(self, prev, cur, mode):
        self.action_listener(True, cur)
        if (mode == 'Volume'):
            if prev == cur:
                if (self.vk % 3 == 0):
                    self.volume_change_factor = min(4, self.volume_change_factor * 2)
                self.vk += 1
            else:
                self.volume_change_factor = 1
                self.vk = 1
        elif (mode == 'Brightness'):
            if prev == cur:
                if (self.bk % 2 == 0):
                    self.brightness_change_factor = min(30, self.brightness_change_factor + 10)
                self.bk += 1
            else:
                self.brightness_change_factor = 10
                self.bk = 1
        elif (mode == 'Scroll'):
            if prev == cur:
                if (self.sk % 2 == 0):
                    self.scroll_change_factor = int(self.scroll_change_factor * 1.5)
                self.sk += 1
            else:
                self.scroll_change_factor = 150
                self.sk = 1

    def volume_change(self, incOrDec):
        for i in range(self.volume_change_factor):
            if incOrDec == 'Increase':
                keyboard.press(Key.media_volume_up)
                keyboard.release(Key.media_volume_up)
            elif incOrDec == 'Decrease':
                keyboard.press(Key.media_volume_down)
                keyboard.release(Key.media_volume_down)

    def brightness_change(self, incOrDec):
        if incOrDec == 'Increase':
            sbc.set_brightness(min(100, sbc.get_brightness() + self.brightness_change_factor))
        elif incOrDec == 'Decrease':
            sbc.set_brightness(max(0, sbc.get_brightness() - self.brightness_change_factor))

    def mouse_pointer(self, x1, y1):
        cv2.rectangle(img, (self.frameR, self.frameR), (wCam - self.frameR, hCam - self.frameR), (255, 0, 255), 2)
        # Convert Coordinates
        x = np.interp(x1, (self.frameR, wCam - self.frameR), (0, wScr))
        y = np.interp(y1, (self.frameR, hCam - self.frameR), (0, hScr))
        # Smoothen Values
        clocX = self.plocX + (x - self.plocX) / self.smoothening
        clocY = self.plocY + (y - self.plocY) / self.smoothening
        self.plocX, self.plocY = clocX, clocY
        # Move Mouse
        autopy.mouse.move(wScr - clocX, clocY)
        self.action_listener(False, 'Mouse Pointer')
        cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)

    def keyoard_press(self, img, lmList):
        global buttonPressed, capslock_boolean
        for button in buttonList:
            x, y = button.pos
            w, h = button.size

            if x < lmList[8][0] < x + w and y < lmList[8][1] < y + h:
                cv2.rectangle(img, (x - 5, y - 5), (x + w + 5, y + h + 5), (175, 0, 175), cv2.FILLED)
                cv2.putText(img, button.text, (x + 20, y + 65),
                            cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 4)
                lengthu, lineInfo, img = detector.findDistance(lmList[8][0:2], lmList[12][0:2], img)
                lengthd, lineInfo, img = detector.findDistance(lmList[5][0:2], lmList[9][0:2], img)
                ratio = lengthu / lengthd

                if ratio < 1.1:
                    cv2.rectangle(img, button.pos, (x + w, y + h), (0, 255, 0), cv2.FILLED)
                    cv2.putText(img, button.text, (x + 20, y + 65),
                                cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 4)
                    if button.text.strip() == 'SPACE':
                        keyboard.press(Key.space)
                    elif button.text.strip() == 'ENTER':
                        keyboard.press(Key.enter)
                    elif button.text.strip() == 'CAPS':
                        capslock_boolean = not capslock_boolean
                    elif button.text.strip() == '<--':
                        keyboard.press(Key.backspace)
                        keyboard.release(Key.backspace)
                    else:
                        if capslock_boolean:
                            keyboard.press(button.text)
                        else:
                            keyboard.press(button.text.lower())
                    self.action_listener(True, 'Key Pressed is : ' + button.text, butDelay=15)

    def start_controller(self, img, one_or_two, isRightHand, fingers1, lmList1, fingers2=None, lmList2=None):
        global buttonPressed, prev_frame

        if self.keyboard_mode == False:
            if buttonPressed is False:
                if fingers1.count(1) == 5:
                    self.action_listener(False, 'Neutral')

                elif fingers1.count(1) == 0:
                    if prev_frame == 'V':
                        pyautogui.mouseDown()
                        self.action_listener(False, 'Drag')
                    elif prev_frame == 'Drag':
                        self.mouse_pointer(lmList1[8][0], lmList1[8][1])
                        self.action_listener(False, 'Drag', text_y_cood=150)
                    elif prev_frame == 'Neutral':
                        self.action_listener(True, 'ScreenShot')
                        screenshot = pyautogui.screenshot()
                        curr_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                        filename = curr_datetime + '.png'
                        path = os.path.join(os.environ['USERPROFILE'], "Pictures/Screenshots/", filename)
                        screenshot.save(path, 'PNG')

                # Only Index Finger : Moving Mode
                elif fingers1[1] == 1 and fingers1.count(1) == 1 and (
                        prev_frame == 'Mouse Pointer' or prev_frame == 'Neutral'):
                    self.mouse_pointer(lmList1[8][0], lmList1[8][1])

                # V two Fingers
                elif fingers1[1] == 1 and fingers1[2] == 1 and fingers1.count(1) == 2:
                    if prev_frame == 'Drag':
                        pyautogui.mouseUp()
                    lengthu, lineInfo, img = detector.findDistance(lmList1[8][0:2], lmList1[12][0:2], img)
                    lengthd, lineInfo, img = detector.findDistance(lmList1[5][0:2], lmList1[9][0:2], img)
                    ratio = lengthu / lengthd
                    if ratio < 1.1 and prev_frame == 'V':
                        pyautogui.doubleClick()
                        self.action_listener(True, 'Double Left Click')
                    else:
                        self.action_listener(False, 'V')

                # Clicks
                elif fingers1[1] == 1 and fingers1.count(1) == 1 and prev_frame == 'V':
                    if isRightHand:
                        pyautogui.click(button='right')
                        self.action_listener(True, 'Right Click')
                    else:
                        pyautogui.click(button='left')
                        self.action_listener(True, 'Left Click')
                elif fingers1[2] == 1 and fingers1.count(1) == 1 and prev_frame == 'V':
                    if isRightHand:
                        pyautogui.click(button='left')
                        self.action_listener(True, 'Left Click')
                    else:
                        pyautogui.click(button='right')
                        self.action_listener(True, 'Right Click')

                # Scrolling
                elif fingers1 == [0, 1, 1, 1, 0]:
                    if self.dynamic_frames == 0:
                        self.prev_dynamic_x, self.prev_dynamic_y = lmList1[9][0], lmList1[9][1]
                    elif self.dynamic_frames % 5 == 0:
                        dx, dy, sx, sy = self.dynamic_distance(lmList1[9][0], lmList1[9][1])
                        if isRightHand:
                            if abs(dx) > abs(dy):
                                if sx == 1:
                                    self.change_factor(prev_frame, 'Scroll Right', 'Scroll')
                                    mouse.scroll(self.scroll_change_factor / 100 * self.sk, 0)
                                else:
                                    self.change_factor(prev_frame, 'Scroll Left', 'Scroll')
                                    mouse.scroll(-self.scroll_change_factor / 100 * self.sk, 0)
                            else:
                                if sy == 1:
                                    self.change_factor(prev_frame, 'Scroll Up', 'Scroll')
                                    pyautogui.scroll(self.scroll_change_factor)
                                else:
                                    self.change_factor(prev_frame, 'Scroll Down', 'Scroll')
                                    pyautogui.scroll(-self.scroll_change_factor)
                        else:
                            if abs(dx) > abs(dy):
                                if sx == 1:
                                    self.change_factor(prev_frame, 'Volume Increase', 'Volume')
                                    self.volume_change('Increase')
                                else:
                                    self.change_factor(prev_frame, 'Volume Decrease', 'Volume')
                                    self.volume_change('Decrease')
                            else:
                                if sy == 1:
                                    self.change_factor(prev_frame, 'Brightness Increase', 'Brightness')
                                    self.brightness_change('Increase')
                                else:
                                    self.change_factor(prev_frame, 'Brightness Decrease', 'Brightness')
                                    self.brightness_change('Decrease')
                        self.dynamic_frames = 0
                        self.prev_dynamic_x, self.prev_dynamic_y = lmList1[9][0], lmList1[9][1]
                    self.dynamic_frames += 1

                # Shortcuts using Hand Gestures

                # Baba
                elif fingers1 == [0, 1, 0, 0, 1] and prev_frame == 'Neutral':
                    if isRightHand:
                        run("google chrome")
                        self.action_listener(True, 'Open Browser Window', butDelay=15)
                    else:
                        pass

                # Only Thumb
                elif fingers1 == [1, 0, 0, 0, 0] and prev_frame == 'Neutral':
                    if isRightHand:
                        pyautogui.hotkey('ctrl', 't')
                        self.action_listener(True, 'New Tab', butDelay=15)
                    else:
                        pyautogui.hotkey('ctrl', 'w')
                        self.action_listener(True, 'Close Tab', butDelay=15)

                # Call Me
                elif fingers1 == [1, 0, 0, 0, 1] and prev_frame == 'Neutral':
                    if isRightHand:
                        run('whatsapp')
                        self.action_listener(True, 'Messaging Apps Open', butDelay=15)
                    else:
                        run('calculator')
                        self.action_listener(True, 'Calculator Opening', butDelay=15)

        else:
            self.keyoard_press(img, lmList1)


detector = HTM2.HandDetector(detectionCon=0.9, maxHands=2)
gesture_controller = GestureController()

while True:
    # Find hand Landmarks
    success, img = cap.read()
    hands, img = detector.findHands(img)

    if gesture_controller.keyboard_mode:
        img = drawKeyBoard(img, buttonList)
        if capslock_boolean:
            cv2.putText(img, "CAPS LOCK IS ON", (500, 600), cv2.FONT_HERSHEY_PLAIN, 3, (255, 255, 0), 3)

    # Delay for next action
    if buttonPressed:
        cv2.putText(img, prev_frame, (20, 100), cv2.FONT_HERSHEY_PLAIN, 3, (255, 255, 0), 3)
        buttonCounter += 1
        if buttonCounter > buttonDelay:
            buttonPressed = False
            buttonCounter = 0
    else:
        if hands:
            # Hand 1
            hand1 = hands[0]
            handType1 = hand1["type"]  # Handtype Left or Right
            lmList1 = hand1["lmList"]  # List of 21 Landmark points
            bbox1 = hand1["bbox"]  # Bounding box info x,y,w,h
            centerPoint1 = hand1['center']  # center of the hand cx,cy
            fingers1 = detector.fingersUp(hand1)

            # Hand 2
            if len(hands) == 2:
                hand2 = hands[1]
                handType2 = hand2["type"]  # Hand Type "Left" or "Right"
                lmList2 = hand2["lmList"]  # List of 21 Landmark points
                bbox2 = hand2["bbox"]  # Bounding box info x,y,w,h
                centerPoint2 = hand2['center']  # center of the hand cx,cy
                fingers2 = detector.fingersUp(hand2)

            if len(hands) == 1:
                gesture_controller.start_controller(img, 1, handType1 == 'Right', fingers1, lmList1)
            elif len(hands) == 2:
                if fingers1.count(1) == 5 and fingers2.count(1) == 5:
                    gesture_controller.keyboard_mode = not gesture_controller.keyboard_mode
                    gesture_controller.action_listener(True, 'Changing Mode Wait', butDelay=15)
                if gesture_controller.keyboard_mode:
                    set_KeyBoard()
                else:
                    set_Mouse()

    # Frame Rate
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, 'FPS:' + str(int(fps)), (20, 50), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 0), 3)

    # Display
    cv2.imshow("Gesture Controller", img)
    if cv2.waitKey(1) & 0xFF == 27:
        break
