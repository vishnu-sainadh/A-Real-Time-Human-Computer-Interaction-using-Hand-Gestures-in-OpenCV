"""Virtual on-screen keyboard: button model, key layout, and rendering."""

import cv2
import cvzone
import numpy as np


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
