'''
这个模块用于完成变换矩阵的相关设置，可以广义扩展成变换，提供扩展接口
'''

import numpy as np 

class TransformationMatrix:
    '''
    一个3x3变换矩阵类型,包含了许多边界接口

    方法:
    1. to_abspos(pos) 根据
    '''
    E = np.identity(3)
