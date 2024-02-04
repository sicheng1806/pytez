'''
这个模块实现了用于管理绘图状态的上下文管理器，用于记录Canvas的状态。
'''

from .transform import TransformationMatrix
from .style import DefaultStyle


class CanvasCtx():
    '''
    Canvas的上下文管理器类型，由StyleCtx、PosCtx和BasicCtx组成，由其统一组织接口。

    记录坐标、样式、canvas的设置的状态信息

    属性
    ------
    1. ``pos_ctx`` : PosCtx
       管理坐标状态的上下文管理器
    2. ``style_ctx``
       管理样式状态的上下文管理器
    3. ``basic_ctx``
       管理debug和background的上下文管理器

    方法
    -------
    1. ``get_pos_ctx()`` 返回具有变换矩阵和当前坐标的上下文管理器
    2. ``get_style_ctx()`` 返回样式的上下文管理器 
    3. ``get_basic_ctx()`` 返回调试和长度的上下文管理器类型 
    4. ``get_tmat()`` 返回变换矩阵
    5. ``get_curpos()`` 返回当前位置
    6. ``get_curstyle()`` 返回当前样式
    7. ``get_debug()`` 返回是否为调试状态
    8. ``get_origin()`` 返回原点位置
    9. ``get_ctx()`` 以字典形式返回储存的值
    10. ``get_bounds()`` 返回坐标系边界
    11. ``set_debug(d)`` 开启调试模式
    12. ``set_ctx(...)`` 用于设置上下文管理器的值
    13. ``set_style(fill,stroke,**kwargs)`` 设置样式
    14. ``set_transform(mat)`` 设置变换矩阵
    15. ``moveto(pos)`` 设置当前位置
    16. ``set_bounds(x,y)`` 设置坐标系边界
    16. ``set_background(color)`` 设置背景色
    '''
    def __init__(self,debug=False,background='w',zorder=0,transform=TransformationMatrix.E,curpos=(0,0),style=DefaultStyle()) -> None:
        '''
        参数
        ------
        
        debug : bool 
            调试属性,默认为False
        
        background : color
            背景色
        
        transform : (3,3)数组
            坐标系的变换矩阵，默认为单位矩阵
        
        curpos : (float,float)
            当前坐标，默认为 (0,0)
        
        style : dict 
            当前样式，默认为默认样式文件储存的样式
        '''
        pass
    
    def get_pos_ctx(self):
        '''返回具有变换矩阵和当前坐标的上下文管理器'''
    def get_style_ctx(self):
        '''返回样式的上下文管理器 '''
    def get_basic_ctx(self):
        pass 
    def get_ctx(self):
        pass 
    def get_tmat(self):
        pass 
    def get_bounds(self):
        pass 
    def get_origin(self):
        pass 
    def get_curpos(self):
        pass 
    def get_curstyle(self):
        pass 
    def get_debug(self):
        pass 
    def get_backgroud(self):
        pass 
    def get_zorder(self):
        pass 
    def set_ctx(self,mat=None,style=None,debug=None,zorder=None,backgroud=None):
        pass 
    def set_zorder(self):
        pass 
    def set_debug(self,open):
        pass 
    def set_background(self,bk):
        pass 
    def set_transform(mat):
        pass 
    def set_bounds(bounds):
        '''设置坐标系边界'''
        pass 
    def moveto(self):
        pass 
    def set_style(self,fill=None,stroke=None,**style_special):
        pass 
    


class Context:
    '''
    上下文管理器，用于储存状态量
    '''
    def __init__(self,attr_names,attr_values) -> None:
        '''
        给定属性名称和属性初值建立上下文管理器
        '''
        if len(attr_names) != len(attr_values):
            raise AttributeError("参数attr_name和attr_value必须等长")
        self._attrs_dict = dict(zip(attr_names,attr_values))
        self._checkfunc = dict(zip(attr_names,[None]*len(attr_values)))
    
    def _existed_attr_name(self,attr_name):
        '''
        检测属性名称是否存在，若不存在则报错
        '''
        if attr_name not in self._attrs_dict:
            raise KeyError(f"属性名称{attr_name}并未注册")
        return True 

    def set_check(self,attr_name,check_func):
        '''
        为指定的属性设置检查合法性的函数
        '''
        self._existed_attr_name(attr_name)
        self._checkfunc[attr_name] = check_func
    
    def set_value(self,attr_name,value):
        '''
        未指定的属性设置新值
        '''
        self._existed_attr_name(attr_name)
        if self.check_func[attr_name] is not None:
            self._checkfunc[attr_name]
        self._attrs_dict[attr_name] = value
        
    def get_value(self,attr_name):
        '''获取指定属性名称的值'''
        self._existed_attr_name(attr_name)
        return self._attrs_dict[attr_name]
    def register_attr(self,attr_name,attr_value,check_func=None):
        '''注册一个新的属性名称，若属性名称已经存在则报错'''
        if attr_name in self._attrs_dict:
            raise AttributeError(f"属性名称冲突：{attr_name} 已经存在")
        self._attrs_dict[attr_name] = attr_value
        self._checkfunc[attr_name] =  check_func
    def pop_attr(self,attr_name):
        '''删除一个属性，并返回其值'''
        self._existed_attr_name(attr_name)
        self._checkfunc.pos(attr_name)
        return self._attrs_dict.pop(attr_name)
    
class PosCtx():
    '''
    记录坐标系统状态的类，由变换矩阵、当前位置和边界组成
    
    用法
    -----
    创建并使用tmat,curpos,
    '''
    def __init__(self,transform=TransformationMatrix.E,curpos=(0,0),bounds=(None,None)) -> None:
        self._ctx = Context(attr_names=["transform","curpos","bounds"],attr_values=[transform,curpos,bounds])
        self._ctx.set_check("transform",self.check_transform)
        self._ctx.set_check("curpos",self.check_curpos)
        self._ctx.set_check("bounds",self.check_bounds)
    @property
    def transform(self):
        return self._ctx.get_value("transform")
    @property
    def curpos(self):
        return self._ctx.get_value("curpos")
    @property
    def bounds(self):
        return self._ctx.get_value("bounds")
    def check_transform(self,transform):
        return True 
    def check_curpos(self,curpos):
        return True
    def check_bounds(self,bounds):
        return True 
    def get_transform(self):
        return self.transform
    def get_curpos(self):
        return self.curpos
    def get_bounds(self):
        return self.bounds
    def set_transform(self,transform):
        return self._ctx.set_value("transform",transform)
    def set_curpos(self,curpos):
        return self._ctx.set_value("curpos",curpos)
    def set_bounds(self,bounds):
        return self._ctx.set_value("bounds",bounds)

class StyleCtx():
    '''记录样式状态的类，由fill，stroke和style_special组成'''
    def __init__(self,fill,stroke,**style_special) -> None:
        pass
class BasicCtx():
    '''记录debug、background、bounds状态的类'''
    pass 