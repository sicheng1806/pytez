'''
这个模块提供坐标的各种表示(除了锚点),以及一些坐标计算支持

提供了一个解析坐标的函数: parse_pos(pos_dct,transform,curpos,anchors)
'''
from .transform import TransformationMatrix
import numpy as np 

class StatusError(Exception):
    pass
class AbsposError(AttributeError):
    pass 

def isValid(self,pos_dct):
    '''
    对坐标字典进行预处理，返回合法的预处理后的坐标，否则报错
    '''
    pass
def _parse_polar_to_rect(theta,radius):
    '''将极坐标转化为直角坐标'''
    pass
def parse_pos(pos_dct,transform:TransformationMatrix,curpos):
    '''给定坐标字典或元组、变换矩阵、当前坐标'''
    pos_dct = isValid(pos_dct)
    if pos_dct["abs"]  :
        _must_transform = False
    else:
        _must_transform = True
    if pos_dct["rel"] : 
        _must_curpos = True
    else:
        _must_curpos = False
    if pos_dct["polar"] : 
        pos_dct["x"],pos_dct["y"] = _parse_polar_to_rect(pos_dct["theta"],pos_dct["radius"])
    # 现在只需要将pos转化为abspos
    pos = pos_dct["x"],pos_dct["y"]
    if _must_transform:
        if not isinstance(transform,TransformationMatrix):
            transform = TransformationMatrix(transform)
        pos = transform.to_abspos(pos)
    if _must_curpos:
        pos = pos[0]+curpos[0],pos[1]+curpos[1]
    return pos 

def must_abspos(self,abspos):
    abspos = np.array(abspos)
    if abspos.shape is not (2,):
        raise AbsposError(f"{abspos} 并非合法的坐标")
    



class Position():
    '''
    一个支持Canvas的坐标表示的类型，接入表示坐标的字典返回绝对坐标

    功能
    ------
    接收坐标表示，根据变换矩阵、当前位置、锚点、返回绝对坐标

    用法
    ------
    使用表示坐标的字典来表示坐标，初始化后传入坐标字典，调用其方法获取各种形式的键

    属性
    ------
    1. ``xs``
    2. ``ys``
    3. ``abspos_lst``

    方法
    ------
    1. ``add_pos(pos_dct)`` 添加坐标
    2. ``extend_pos(pos_dct_lst)`` 添加若干坐标
    3. ``update_pos(pos_dct_lst)`` 更新坐标
    4. ``update_status(transform=None,anchor_lst=None,curpos=None)`` 更新坐标系状态
    5. ``update_anchors(anchors)`` 更新锚点列表
    6. ``add_anchor(anchor)`` 增加锚点
    7. ``extend_anchors(anchors)`` 添加锚点
    8. ``clear_anchors()``
    9. ``isValid(pos_dct)`` 检测传入坐标字典是否合理
    10. ``update_curpos(pos_dct)`` 更新当前坐标
    11. ``update_transform(tmat)`` 更新当前变换矩阵
 
    坐标字典
    ----------
    坐标字典是指将表示坐标的各种方法用字典的键的形式储存，
    当遇到字典键冲突时为无效字典，传入Position类会报错，
    当遇到字典键不足以确定坐标时会使用默认值补全，字典的默认值为update=True,rel=False,abs=False,x = 1,y = 1。
    abs和rel键也可以传入坐标，不过在处理使会转变为bool值。空字典为当前坐标而不是默认值填满的坐标。
    '''

    def __init__(self,xs=[],ys=[],transform=None,anchor_lst=None,curpos=None) -> None:
        '''
        参数
        -------
        传入x,y的绝对数据坐标系坐标作为初始值，默认为空列表
        '''
        _posdcts = [{"x":x,"y":y} for x,y in zip(xs,ys)]
        self._transform = transform
        self._anchors = anchor_lst
        self._curpos = curpos
        self._abspos_lst = self.update_pos(_posdcts)
    
    @property
    def status(self):
        return {"transform":self._transform,"anchors":self._anchors,"curpos":self._curpos}
    @property
    def abspos_lst(self):
        return self.abspos_lst
    
    def get_pos(self,index=-1):
        '''返回坐标值，默认为最后一项'''

    def isValid(self,*pos_dct):
        
        return pos_dct
    
    def isok_status(self):
        if self._transform is None or self._anchors is None or self._curpos is None:
            raise StatusError("Position状态还未准备完成")

    def add_pos(self,pos_dct):
        '''添加一个新的坐标'''
        self.isok_status()
        pos_dct = self.isValid(pos_dct)
        if "anchor" in pos_dct:
            self._abspos_lst.append(self.parse_anchor(anchor=pos_dct["anchor"]))
        else: 
            self._abspos_lst.append(self.parse_pos(pos_dct=pos_dct))
        


    def update_pos(self,pos_dct):
        '''解析坐标字典，检测冲突，如果坐标有效则更新状态，返回绝对数据坐标'''
        return []

    def parse_pos(self,pos_dct):
        '''
        解析不同形式表达的坐标,返回绝对数据坐标
        '''
        pass
    
    def parse_anchor(self,anchor):
        '''
        解析锚点表示的坐标
        '''
        pass
    
    def _parse_rel_to_pos(self,rel_pos,curpos):
        '''
        将相对数据坐标系相对坐标解析为相对数据坐标系坐标
        '''
        pass
    def _parse_polar_to_rect(self,polar_pos):
        '''将极坐标解析为直角坐标'''
        pass


    
