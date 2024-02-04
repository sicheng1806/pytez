'''
这个模块用于提供样式管理器类，其任务是从默认样式文件获取样式，临时储存当前样式，获取当前样式，将当前样式存储为默认样式文件或者样式文件。
'''

from collections import UserDict
import json
from pathlib import Path

class DefaultStyle(UserDict):
    '''
    一个管理默认字典的类

    导入默认字典文件，管理默认字典文件的读写

    使用方法
    ----------
    创建时就根据fname导入默认样式配置，
    之后可以按字典类型操作。
    需要更改默认配置文件时，调用其相关方法

    类属性
    ------
    1. DefaultStylePath : 设计时规定的默认样式配置文件的路径

    类方法
    -------
    1. recoverDefaultStyle : 用备份默认样式配置文件复原默认样式配置文件
    
    属性
    ---------
    1. fname : 用户指定的默认样式配置文件路径，默认为设计时规定路径
    2. data : 储存样式的字典,不建议使用

    方法
    --------
    1. saveto(fname=None) 将默认配置文件保存到fname路径

    默认样式配置字典示例：

    {
    "fill" : null ,
    "stroke" : "1pt+luma(0%)",
    "radius" : 1,
    "shorten" : "LINEAR",
    "padding" : null,
    "circle" : {
        "radius" : "auto" ,
        "stroke" : "auto" ,
        "fill" : "auto" 
        }
    }

    '''
    DefaultStylePath = Path("./pytez/DefaultStyleDict.json") 
    assert DefaultStylePath.exists() 
    
    def __init__(self,fname=None) -> None:
        '''
        参数
        -------
        fname : filepath ; 默认为None
            默认样式配置的json文件路径，如果为None则使用 DefaultStylePath
        '''
        self.fname = self.DefaultStylePath if fname is None else fname 
        with open(self.fname) as f:
            data = json.loads(f.read())
            self.data = self.parse_style(data)

    def saveto(self,fname=None):
        '''
        保存当前样式为默认样式，如果fname为None则保存为fname属性的值。
        '''
        fname = fname if fname else self.fname
        with open(fname,"w") as f:
            f.write(json.dumps(self.data,indent=4))
    
    @classmethod
    def recoverDefaultStyle(self):
        '''恢复配置文件为最初的设置'''
        import shutil
        shutil.copyfile(self.DefaultStylePath.parent/"DefaultStyleDict copy.json",self.DefaultStylePath)


class StyleManager():
    '''
    一个用于将pytez类型样式转化为无冲突的mpl样式的类型

    功能
    ------
    结合当前样式将样式参数解析为mpl的样式字典。

    使用方法
    ----------
    初始化后直接调用其方法


    方法
    ------
    1.parse_style(curstyle=None,**style_dct) 将pytez样式解析为mpl样式
    '''
    def __init__(self):
        pass
    
    def parse_style(self,curstyle,style_dct):
        pass


