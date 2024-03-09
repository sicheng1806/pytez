import matplotlib.patches as mpatch
from matplotlib.path import Path
from collections.abc import Iterable
import re 
from argument import standardize_drawable,standardize_xy
from bezier import segments_to_coefs,coefs_to_center,coefs_to_length_and_nodeweight,get_bezier_point,bezier_line_intersection
from argument import RE_float,RE_node_name,RE_anchor_name
import numpy as np 




class Node():
    '''图案类，能够直接调用绘制图形'''

    def __init__(self,drawables,name = None ,anchor_center = None) -> None:
        if name is not None: 
            if not isinstance(name,str) or not re.fullmatch(RE_node_name,name) : raise ValueError(f"{name}不是支持的Node名")
        self.name = name
        self.drawables = [standardize_drawable(drawable) for drawable in drawables] # 标准化drawable
        self.artists = [self._drawable_to_artist(d) for d in self.drawables]
        # 锚点预准备
        ## 如果是组(不连续)，则计算路径为边框，其他为路径本身
        ## 如果是连续不闭合路径，则允许路径计算
        ## 如果连续且闭合，则允许面积相关计算
        ## 组和闭合路径允许面积相关计算
        ## 不闭合路径只允许路径计算
        ## _iscontinued,_isgroup,_isclosed,_can_get_intersection,_coefs
        data_segments = []
        for drawable in self.drawables:
            data_segments.extend(drawable["segments"])
        self._iscontinued,self._isclosed = self._is_segments_continued_and_closed(data_segments)
        if not self._iscontinued:
            self._isgroup = True
            self._can_get_intersection = True
            self._coefs = segments_to_coefs(self._get_bounding_segments()) # 路径为边框
        else:
            self._isgroup = False
            self._coefs = segments_to_coefs(data_segments)
            self._can_get_intersection = True if self._isclosed else False 
        ## 设置锚点字典
        self._anchor_dct = {}
        ## 如果可以获取交点，则具有 _center
        if self._can_get_intersection:
            self._center = coefs_to_center(self._coefs)
        ## 路径计算用的总长度，结点权重
        self._length,self._nodeweight,self._length_error = coefs_to_length_and_nodeweight(self._coefs)
        
    # 自我描述
    def get_description_dict(self):
        '''
        返回具有描述性的字典
        '''
        return {
            "name":self.name,
            "drawables":self.drawables
        }
    def __str__(self):
        return f"{self.__class__}({self.get_description_dict()})"

    # 与artist交互
    ## 返回生成的artist
    def get_artists(self):
        return self.artists
    def iter_artists(self):
        for a in self.artists:
            yield a
    ## 参数转化
    def _stroke_to_mpl_args(self,paint,thickness,cap,dash,join):
        return {"edgecolor":paint,"linewidth":thickness,"capstyle":cap,"linestyle":dash,"joinstyle":join}
    def _fill_to_mpl_args(self,fill):
        if fill is None:
            return {"facecolor":None,"fill":False}
        else:
            return {"facecolor":fill,"fill":True}
    ### Path生成
    def  _segments_to_path(self,segments):
        vects = []
        codes = []
        if not isinstance(segments,Iterable):
            raise TypeError("segments参数类型必需是Iterable的子类")
        for seg in segments:
            # 缺少类型检测
            match seg[0] : 
                case "line" : 
                    if len(seg[1:]) < 2:
                        raise ValueError(f"line类型路径至少需要两个顶点，你的顶点为{seg[1:]}")
                    vects.extend(seg[1:])
                    codes.append(Path.MOVETO)
                    codes.extend([Path.LINETO for i in seg[2:]])
                    assert len(codes) == len(vects)
                case "cubic" :
                    if len(seg[1:]) != 4:
                        raise ValueError("cubic类型路径有且仅有四个顶点")
                    vects.extend([seg[1],seg[3],seg[4],seg[2]]) # cetz里面的第二参数为endPoint
                    codes.append(Path.MOVETO)
                    codes.extend([Path.CURVE4]*3)
                    assert len(codes) == len(vects)
                case _: 
                    raise ValueError("字段类型错误")     
        return Path(vects,codes)
    ## 生成artist
    def _drawable_to_artist(self,drawable:dict):
        '''使用已经标准化的drawable生成artist'''
        match drawable["type"] :
            case "path" : 
                path = self._segments_to_path(drawable["segments"])
                stroke_arg_dct = self._stroke_to_mpl_args(**drawable["stroke"]) 
                fill_arg_dct = self._fill_to_mpl_args(drawable["fill"]) # fill,facecolor
                hidden = drawable["hidden"] if "hidden" in drawable else False
                zorder = drawable["zorder"] if "zorder" in drawable else None 
                alpha = drawable["alpha"] if "alpha" in drawable else 1
                kwargs = stroke_arg_dct | fill_arg_dct | {"visible":not hidden,"zorder":zorder,"alpha":alpha}
                a = mpatch.PathPatch(path,**kwargs)
                return a
            case _ :
                raise ValueError(f"{drawable["type"]}不是支持的drawable类型")
    # 边框管理
    def _get_bounding_box(self):
        '''返回Node的边框(xmin,xmax,ymin,ymax)，用于自动调整画布以及部分锚点计算'''
        verts = []
        for d in self.drawables:
            for seg in d["segments"]:
                verts.extend(seg[1:])
        xs,ys = zip(*verts)
        return (min(xs),min(ys)),(max(xs),max(ys))
    def _get_bounding_segments(self):
        xmin,xmax,ymin,ymax = self._get_bounding_box()
        return [("line",(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax),(xmin,ymin))]
    def get_lim(self):
        return self._get_bounding_box()
    # 锚点
    ## 锚点字典
    def _update_anchor_dct(self,anchor,xy):
        if not re.fullmatch(RE_anchor_name,anchor): raise ValueError("锚点的命名不符合规范")
        xy = standardize_xy(xy)
        self._update_anchor_dct[anchor] = xy
    def add_anchor(self,anchor,xy):
        return self._update_anchor_dct(anchor,xy)
    ## segments判断函数
    def _is_segments_continued_and_closed(self,segments):
        start_points ,end_points = [],[]
        _continue = True
        _joint = True
        for code in segments:
            start_points.append(code[1])
            match code[0]:
                case "line" : end_points.append(code[-1])
                case "cubic" : end_points.append(code[2])
                case _ : raise 
        if tuple(end_points[-1]) != tuple(start_points[0]) : _joint = False
        for i in range(1,len(start_points)):
            if tuple(start_points[i]) != tuple(end_points[i-1]) : _continue = False
        return _continue , (_joint and _continue)
    ## 返回锚点值
    def calculate_anchors(self,anchor=None):
        '''根据anchor的值返回坐标'''
        default_anchors = {'center':None,'north':'90deg','south':'-90deg','west':'180deg','east':'0deg','start':0,'mid':'50%','end':'100%'}
        if anchor in default_anchors: anchor = default_anchors[anchor]
        if anchor is None: 
            if self._can_get_intersection: return self._center
            else: return self.get_point('50%')
        anchor = str(anchor)
        if re.fullmatch(RE_float,anchor):
            return self.get_point(float(anchor)) #长度
        if re.fullmatch(RE_float+"%",anchor):
            return self.get_point(anchor) # 百分数
        if self._can_get_intersection:
            if re.fullmatch(RE_float+'rad',anchor):
                rad = float(anchor[:-3])
                rs = self.get_point_by_rad(rad)
                if len(rs) != 1: raise ValueError(f"由{anchor}锚点所确定的值不唯一，结果为{rs}")
                return rs[0]
            if re.fullmatch(RE_float+'deg',anchor):
                rad = np.radians(float(anchor[:-3]))
                rs = self.get_point_by_rad(rad)
                if len(rs) != 1: raise ValueError(f"由{anchor}锚点所确定的值不唯一，结果为{rs}")
                return rs[0]
        if anchor in self._anchor_dct:
            return self._anchor_dct[anchor]
        return TypeError(f"{anchor}不存在，或者未注册")
    # 路径计算
    def get_point(self,t):
        '''根据长度或者百分数计算路径上的点'''
        def _point_by_percent(t):
            assert 0<= t <= 1
            nodeweight = self._nodeweight.copy()
            nodeweight.insert(0,0)
            for i in range(1,len(nodeweight)):
                if t <= nodeweight[i] : break
            t = (t - nodeweight[i-1])/(nodeweight[i] - nodeweight[i-1])
            return get_bezier_point(self._coefs[i-1],t)
        if re.fullmatch(RE_float+"%",str(t)):
            t = float(t[:-1])/100
            return _point_by_percent(t)
        if re.fullmatch(RE_float,str(t)):
            t = float(t)
            if t < 0 : raise ValueError("长度必须大于0")
            if t > self._length : raise ValueError("长度超过曲线的长度")
            t = t/self._length
            return _point_by_percent(t)
        raise TypeError(f"{t}不是支持的参数，支持长度和百分数")
    def get_point_by_rad(self,rad):
        if not self._can_get_intersection: raise NotImplemented("由于node的曲线并不连续且封闭，因而不提供根据角度取值")
        _deg1 = (rad/np.pi)*180 % 360 
        _deg2 = (_deg1 - 90) % 180
        flag = 'x' if 45 <= _deg2 <= 125 else 'y'
        match flag:
            case 'x': 
                _sign = True if  np.cos(rad) > 0 else False
            case 'y':
                _sign = True if np.sin(rad) > 0 else False
        points = []
        line_vect = np.cos(rad) , np.sin(rad)
        line_point = self._center
        for coef in self._coefs:
            result_p = bezier_line_intersection(coef,line_point=line_point,line_vect=line_vect)
            for p in result_p:
                if len(points) == 0 or ( not np.array([ p.all() for p in np.isclose(points,p) ]).any()):
                    # 符号判断
                    match flag:
                        case "x": 
                            if not (((p[0] - line_point[0]) > 0 ) ^ _sign):
                                points.append(p)
                        case "y":
                            if not (((p[1] - line_point[1]) > 0 ) ^ _sign):
                                points.append(p)
                    
        return np.array(points,dtype=float)

        


