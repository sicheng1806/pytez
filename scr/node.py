import matplotlib.patches as mpatch
import numpy as np 
from matplotlib.path import Path
from collections.abc import Iterable
from scipy.integrate import quad
import re 
from matplotlib.colors import to_rgb

from argument import standardize_stroke,standardize_style_dct

RE_float = r"-?(\d+(\.\d+)?|\.\d+)"
RE_anchor = r"[a-z|_|\d]+" #anchor字符串允许的样式


class Node():
    '''图案类，能够直接调用绘制图形'''

    def __init__(self,name = None ,drawables = [] ,anchor_center = None) -> None:
        if not isinstance(name,str) and name is not None:
            raise TypeError("name参数类型为str或者None")
        self.name = name
        self.drawables = []
        # drawable 样式标准化(字典)
        for drawable in drawables:
            self.drawables.append(self._standardize_drawable(drawable))
        #artists生成
        self.artists = [self._drawable_to_artist(d) for d in self.drawables]
        # 锚点预准备
        self._anchor_segments = self.drawables[0]["segments"] if len(drawables) == 1 else self._get_debug_segments() #设置用于锚点计算的字段
        self._anchor_closed = self._is_segments_closed(self._anchor_segments) #检测是否closed
        self._anchor_coeefficients = self._segments_to_coeeficients(self._anchor_segments) #获取多项式系数矩阵
        self._anchor_length,self._anchor_weights = self._coeefficients_to_length_and_weights(self._anchor_coeefficients)
        self._anchor_weight_node = [sum(self._anchor_weights[:i]) for i in range(1,len(self._anchor_weights))]
        self._anchor_weight_node.append(1)
        # 设置路径重心，允许自己设置，这是担心求重心的算法误差大。
        if self._anchor_closed:
            if anchor_center is not None:
                try:
                    anchor_center = np.array(anchor_center,dtype="float")
                    assert anchor_center.shape != (2,)
                except :
                    raise TypeError("anchor_center参数类型必需是位置")
                self._anchor_center = anchor_center
            else:
                self._anchor_center = self.get_closed_segments_center(self._anchor_segments)
        else:
            self._anchor_center = None # 非闭合曲线无center
        self._anchor_dct = {
            "start":self.calculate_anchors(0),
            "mid":self.calculate_anchors("50%"),
            "end":self.calculate_anchors("100%")
        }
        if self._anchor_closed and self._anchor_center is not None:
            self._anchor_dct |= {
                "east": self.calculate_anchors("0deg"),
                "north":self.calculate_anchors("90deg"),
                "south":self.calculate_anchors("-90deg"),
                "west": self.calculate_anchors("180deg")
                }
        
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

    def get_artists(self):
        return self.artists

    def iter_artists(self):
        for a in self.artists:
            yield a

    def _standardize_stroke(self,stroke):
        '''将stroke标准化为键完全的stroke字典'''
        return standardize_stroke(stroke)

    def _stroke_to_mpl_args(self,paint,thickness,cap,dash,join):
        return {"edgecolor":paint,"linewidth":thickness,"capstyle":cap,"linestyle":dash,"joinstyle":join}
    def _fill_to_mpl_args(self,fill):
        if fill is None:
            return {"facecolor":None,"fill":False}
        else:
            return {"facecolor":fill,"fill":True}
    
    def _standardize_drawable(self,drawable):
        '''标准化drawables为字典形式'''
        if "type" not in drawable: raise ValueError("drawable必需type键")
        match drawable["type"]:
            case "path": #!segments,stroke,fill,hidden,zorder,alpha
                if "segments" not in drawable : raise ValueError("drawable缺少segments键")
                if "stroke" not in drawable : drawable["stroke"] = None
                drawable["stroke"] = self._standardize_stroke(drawable["stroke"])
                drawable["fill"] = to_rgb(drawable["fill"]) if "fill" in drawable and drawable["fill"] is not None else None
                drawable["hidden"] = drawable["hidden"] if "hidden" in drawable  else False 
                if not isinstance(drawable["hidden"],bool) : raise TypeError("hidden必需为bool类型")
                drawable["alpha"] = float(drawable["alpha"]) if "alpha" in drawable else 1. 
                drawable["zorder"] = drawable["zorder"] if "zorder" in drawable else None 
                if not isinstance(drawable["zorder"],int) and drawable["zorder"] is not None  : raise TypeError("zorder必需为int类型或None")
            case _ : 
                raise ValueError("drawable的type键错误")
        return drawable

    def _drawable_to_artist(self,drawable:dict):
        '''将drawable转换为artist,drawable必需具有足够的参数'''
        if not isinstance(drawable,dict):
            raise TypeError("drawable参数必须是dict类型")
        match drawable["type"] :
            case "path" : # segments,stroke,fill,hidden,zoder
                path = self._segments_to_path(drawable["segments"])
                stroke_arg_dct = self._stroke_to_mpl_args(**drawable["stroke"]) 
                fill_arg_dct = self._fill_to_mpl_args(drawable["fill"]) # fill,facecolor
                hidden = drawable["hidden"] if "hidden" in drawable else False
                zorder = drawable["zorder"] if "zorder" in drawable else None 
                alpha = drawable["alpha"] if "alpha" in drawable else 1
                kwargs = stroke_arg_dct | fill_arg_dct | {"visible":not hidden,"zorder":zorder,"alpha":alpha}
                a = mpatch.PathPatch(path,**kwargs)
                return a
            case "content":
                raise NotImplementedError()
            case _ :
                raise ValueError(f"{drawable["type"]} : drawable类型不存在")

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

    def _is_segments_closed(self,segments):
        start ,end = [],[]
        for code in segments:
            start.append(code[1])
            match code[0]:
                case "line" : end.append(code[-1])
                case "cubic" : end.append(code[2])
                case _ : raise 
        if tuple(end[-1]) != tuple(start[0]) : return False 
        for i in range(1,len(start)):
            if tuple(start[i]) != tuple(end[i-1]) : return False 
        return True
        
    def _get_debug_box(self):
        '''返回Node的边框(xmin,xmax,ymin,ymax)，用于自动调整画布以及部分锚点计算'''
        verts = []
        for d in self.drawables:
            for seg in d["segments"]:
                verts.extend(seg[1:])
        xs,ys = zip(*verts)
        return (min(xs),min(ys)),(max(xs),max(ys))

    def _get_debug_segments(self):
        xmin,xmax,ymin,ymax = self._get_debug_box()
        return [("line",(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax),(xmin,ymin))]

    def _segments_to_coeeficients(self,segments):
        '''由字段到多项式系数'''
        coeeficients = []
        for seg in segments:
            match seg[0]:
                case "line":
                    for i in range(1,len(seg)-1):
                        coeeficients.append(self._ctrls_to_coeeficient(seg[i],seg[i+1]))
                case "cubic":
                    coeeficients.append(self._ctrls_to_coeeficient(seg[1],*seg[3:],seg[2]))
                case _:
                    raise ValueError("字段类型错误")
        return coeeficients

    def _coeefficients_to_length_and_weights(self,coeefficients):
        lengths = []
        for c in coeefficients:
            x_t_d = np.polynomial.Polynomial(c[0]).deriv(1)
            y_t_d = np.polynomial.Polynomial(c[1]).deriv(1)
            lengths.append(quad(lambda t : np.sqrt((x_t_d(t) ** 2 + y_t_d(t) ** 2)),0,1)[0])
        L = sum(lengths)
        weights = [l/L for l in lengths]
        return L , weights

    def get_point(self,t):
        '''根据参数获取点,t: 长度 或 百分数'''
        def _point_by_percent(t):
            for i in range(len(self._anchor_weight_node)):
                if t <= self._anchor_weight_node[i] : break
            t = 1 - (self._anchor_weight_node[i] - t)/self._anchor_weights[i]
            return np.polynomial.Polynomial(self._anchor_coeefficients[i][0])(t),np.polynomial.Polynomial(self._anchor_coeefficients[i][1])(t)
        
        if isinstance(t,float) or isinstance(t,int):
            if t < 0 : raise ValueError("长度必须大于0")
            if t > self._anchor_length : raise ValueError("长度超过曲线的长度")
            t = t/self._anchor_length
            assert 0<= t <= 1
            return _point_by_percent(t)
        if isinstance(t,str):
            if re.fullmatch(RE_float+"%",t):
                t = float(t[:-1])/100
                return _point_by_percent(t)
        raise TypeError("参数类型错误")
        
    def _ctrls_to_coeeficient(self,*ctrls):
        if len(ctrls) == 1:
            return ctrls[0]
        xs,ys = zip(*ctrls)
        match len(ctrls):
            case 2:
                return (xs[0],xs[1]-xs[0]),(ys[0],ys[1]-ys[0])
            case 3:
                return (xs[0],2*xs[1] - 2*xs[0],xs[0]+xs[2] - 2 * xs[1]),(ys[0],2*ys[1] - 2*ys[0],ys[0] + ys[2] - 2 * ys[1])
            case 4: 
                return (xs[0],3* xs[1] - 3*xs[0] , 3*xs[0] - 6*xs[1] + 3*xs[2] , - xs[0] + 3*xs[1] - 3*xs[2] + xs[3]), \
                        (ys[0],3* ys[1] - 3*ys[0] , 3*ys[0] - 6*ys[1] + 3*ys[2] , - ys[0] + 3*ys[1] - 3*ys[2] + ys[3])
            case _ :
                raise ValueError("ctrl的长度错误，或不支持3次以上的贝塞尔多项式")
    
    def get_intersection_with_poly(self,*cn,main_axis = "y"):
        '''获取与多项式的交点，cs为多项式系数 (1,2,3): 1 + 2*x + 3*x**t,a,b为求值区间,用于无穷区间的求交点
        '''
        def _bezeir_intersection_with_poly(an,bn,cn,main_axis):
            x_t = np.polynomial.Polynomial(an,domain=[0,1],window=[0,1])
            y_t = np.polynomial.Polynomial(bn,domain=[0,1],window=[0,1])
            match main_axis:
                case "y":
                    y_x = np.polynomial.Polynomial(cn) 
                    f_t = y_x(x_t) - y_t 
                case "x":
                    x_y =  np.polynomial.Polynomial(cn)
                    f_t = x_y(y_t) - x_t
                case _:
                    raise ValueError("main_axis参数值错误")   
            roots_t = f_t.roots()
            roots_t = [t.real for t in roots_t if t.imag == 0]
            roots_t = [t for t in roots_t if 0<=t<=1]
            roots = [(x_t(t),y_t(t)) for t in roots_t]
            # 尝试带入第三式来将误差大的排除
            return set(roots) 
        roots = set()
        for cooef in self._anchor_coeefficients:
            for _r in _bezeir_intersection_with_poly(cooef[0],cooef[1],cn,main_axis=main_axis):
                isclose = lambda r : np.isclose(r,_r,10e-5).all()
                if  np.array(list(map(isclose,roots))).any() or len(roots) != 0 : break
                roots.add(_r)
        return roots    
    
    def get_intersection_with_bezeir(self,*cn):
        '''获取与贝塞尔曲线的交点，用于曲线段的求交点'''
        def _bezier_intersection_with_bezeir(cn_1,cn_2):
            x_t1,y_t1 = np.polynomial.Polynomial((cn_1[0])),np.polynomial.Polynomial((cn_1[1]))
            x_t2,y_t2 = np.polynomial.Polynomial((cn_2[0])),np.polynomial.Polynomial((cn_2[1]))
            roots_t =  set((x_t1 - x_t2).roots()) & set((y_t1 - y_t2).roots())
            return set(map(lambda t : (x_t1(t),y_t1(t)),roots_t))
        roots  = set()
        for cn_1 in self._anchor_coeefficients:
            roots = roots.union(_bezier_intersection_with_bezeir(cn_1,cn))
        return roots

    def get_closed_segments_center(self,segments):
        '''返回代表闭合路段的重心'''
        if not self._is_segments_closed(segments): raise ValueError("输入的字段的路径并不闭合")
        coeefients = self._segments_to_coeeficients(segments)
        area = 0 
        intX = 0
        intY = 0
        for co in coeefients:
            x_t,y_t = np.polynomial.Polynomial(co[0]),np.polynomial.Polynomial(co[1])
            dx_t,dy_t = x_t.deriv(1),y_t.deriv(1)
            area += quad(lambda t: y_t(t)*dx_t(t)+ 2*x_t(t)*dy_t(t) , 0,1)[0]
            intX += quad(lambda t: x_t(t)**2*dy_t(t),0,1)[0]/2
            intY += quad(lambda t: -y_t(t)**2*dx_t(t),0,1)[0]/2
        return intX/area,intY/area
    
    def get_point_by_angle(self,angle):
        '''返回闭合路径的指定角度的点,angle参数为弧度制'''
        if not isinstance(angle,int) and not isinstance(angle,float): raise TypeError("angle参数必需为实数")
        a,b = self._anchor_center 
        # 这里因为np.tan(np.pi/2) 并不会报错，而会返回一个极大的数，因此要不要对 x = a ，这种特殊情况处理存疑。
        angle %= (2*np.pi) # [0,2*np.pi)
        if angle == np.pi/2 or angle == 3*np.pi/2:
            rs =  self.get_intersection_with_poly(a,main_axis="x")
        else:
            _angle = angle if 0 <= angle < np.pi/2 else angle - np.pi
            cn = (b - a*np.tan(_angle),np.tan(_angle))
            rs =  self.get_intersection_with_poly(*cn)
        if 0 < angle < np.pi : return [p for p in rs if p[1] > b]
        elif 2*np.pi > angle > np.pi : return [p for p in rs if p[1] < b]
        elif angle == 0 : return [p for p in rs if p[0] > a]
        else: return [p for p in rs if p[0]<a]

    def _update_anchor_dct(self,anchor,xy):
        if not re.fullmatch(RE_anchor,anchor): raise ValueError("锚点的命名不符合规范")
        try:
            xy = np.array(xy,dtype="float")
            if xy.shape != (2,) : raise 
        except :
            raise TypeError("坐标点格式错误")
        self._update_anchor_dct[anchor] = xy

    def get_lim(self):
        return self._get_debug_box()
    
    def calculate_anchors(self,anchor=None):
        '''根据anchor的值返回坐标'''
        if anchor is None or anchor == 'center': # None
            if  self._anchor_center is not None: return self._anchor_center
            else: return self._anchor_dct["mid"]
        elif isinstance(anchor,int) or isinstance(anchor,float): # 长度
            if anchor < 0 :
                raise ValueError("长度不能小于0")
            return self.get_point(anchor)
        elif isinstance(anchor,str): 
            if re.fullmatch(RE_float+"%",anchor): # 百分数
                return self.get_point(anchor)
            elif re.fullmatch(RE_float+"rad",anchor): #弧度制
                anchor = float(anchor[:-3])
                rs = self.get_point_by_angle(anchor)
                if len(rs) > 1: raise ValueError(f"由角度{(anchor/np.pi)*180}deg获得锚点不唯一")
                return rs[0]
            elif re.fullmatch(RE_float+"deg",anchor): #角度制
                anchor = np.radians(float(anchor[:-3]))
                rs = self.get_point_by_angle(anchor)
                if len(rs) > 1: raise ValueError(f"由角度{(anchor/np.pi)*180}deg获得锚点不唯一")
                return rs[0]
            elif anchor in self._anchor_dct: # 命名字典
                return self._anchor_dct[anchor]
            else:
                raise ValueError("锚点格式错误或者不存在")
        else:
            raise TypeError()    

    def add_anchor(self,anchor,xy):
        return self._update_anchor_dct(anchor,xy)
