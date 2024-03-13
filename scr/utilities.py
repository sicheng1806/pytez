
import numpy as np
import re
from collections.abc import Iterable
from matplotlib.path import Path

RE_float = r"-?(\d+(\.\d+)?|\.\d+)"



# segment和CV
def check_CV(CV):
    _support_codes = {"moveto":1,"line": 2,"cubic":4}
    try:
        codes,vects = CV
        if len(codes) != len(vects): raise 
    except :
        raise TypeError(f"参数codes和vectes必需是长度等长的数列")
    for i in range(len(codes)):
        if codes[i] in _support_codes: codes[i] = _support_codes[codes[i]] # 替换字符串
        if codes[i] not in _support_codes.values(): raise ValueError(f"{codes[i]}不是支持的代码类型,支持的类型为{_support_codes}")
    return codes,vects
        
def check_segment(segment):
    _segment = []
    try:
        for seg in segment:
            if seg[0] not in ("line","cubic"): raise TypeError(f"{seg[0]}不支持的格式")
            _segment.append((seg[0],*[to_xy(xy) for xy in seg[1:]]))
    except Exception as e: 
        raise ValueError(f"segment不符合格式要求:{e}")
    return _segment

def codes_vects_to_segment(codes,vects):
    codes,vects = check_CV((codes,vects))
    def _pop_onetype_segs(codes,vects,last_endp = None):
        while codes[0] == 1: 
            last_endp = vects[0]
            codes = codes[1:]
            vects = vects[1:]
        if last_endp is None :  raise ValueError(f"路径无起始点,codes[0] != moveto (or 1)")
        for i in range(1,len(codes)): # i 是 相同code的长度
            if codes[i] != codes[0]: break
        i = i + 1 if i == len(codes) - 1 else i 
        _type = codes[0]
        _vects = list(vects[:i])
        _vects.insert(0,last_endp)
        last_endp = _vects[-1]
        codes,vects = codes[i:],vects[i:]
        match _type:
            case 2:
                if i < 1 : raise ValueError(f"line路径至少需要两个点")
                segs = [["line"]]
                segs[0].extend(_vects)
            case 4:
                if i % 3 != 0 : raise ValueError(f"curbic路径有且只有4个参数,在这里i%3 == 0,你的 i = {i}")
                segs = [["cubic",_vects[3*i],_vects[3*i+3],_vects[3*i+1],_vects[3*i+2]] for i in range(i // 3)]
            case _:
                raise ValueError(f"{codes[2]}不支持的codes类型")
        return segs,codes,vects,last_endp
    segs = []
    last_endp = None
    while len(codes):
        _segs,codes,vects,last_endp = _pop_onetype_segs(codes=codes,vects=vects,last_endp=last_endp)
        segs.extend(_segs)
    return segs

def segment_to_CV(segment):
    vects = []
    codes = []
    if not isinstance(segment,Iterable):
        raise TypeError("segment参数类型必需是Iterable的子类")
    for seg in segment:
        match seg[0] : 
            case "line" : 
                if len(seg[1:]) < 2:raise ValueError(f"line类型路径至少需要两个顶点，你的顶点为{seg[1:]}")
                # 相连则舍弃开始的一点
                if len(vects) == 0 or (vects[-1] != seg[1]).any():  # 无点或者不相接
                    vects.append(seg[1])
                    codes.append(Path.MOVETO)
                vects.extend(seg[2:])
                codes.extend([Path.LINETO for i in seg[2:]])
                assert len(codes) == len(vects)
            case "cubic" :
                if len(seg[1:]) != 4:raise ValueError("cubic类型路径有且仅有四个顶点")
                if len(vects) == 0 or (vects[-1] != seg[1]).any():  # 无点或者不相接
                    vects.append(seg[1])
                    codes.append(Path.MOVETO)
                vects.extend([seg[3],seg[4],seg[2]]) # cetz里面的第二参数为endPoint
                codes.extend([Path.CURVE4]*3)
                assert len(codes) == len(vects)
            case _: 
                raise ValueError("字段类型错误")
    return codes,vects

# xy,angle
def to_xy(xy):
    try:
        xy = np.array(xy,dtype=float)
        if xy.shape != (2,): raise 
    except :
        raise TypeError(f"{xy} if a bad value for (x,y)")
    return xy 

def to_rad(angle):
    if isinstance(angle,str):
        _angle = angle
        if re.fullmatch(RE_float+r"deg",angle):
            angle =  np.radians(float(angle[:-3]))
        elif re.fullmatch(RE_float+r"rad",angle):
            angle = float(angle[:-3])
    try:
        angle = float(angle)
    except : 
        raise ValueError(f"{_angle}不是合法的angle值")
    return angle


if __name__ == '__main__':
    pass
