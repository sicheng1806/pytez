'''此模块提供三次贝塞尔曲线和直线之间相交的情况'''
import numpy as np
from scipy.integrate import quad

from utilities import to_xy



def check_bezier_coef(coef):
    try:
        coef = np.array(coef,dtype=float)
        if len(coef.shape) != 2 or coef.shape[0] != 2 or coef.shape[1] > 4 : raise 
    except:
        raise ValueError(f"{coef}不是合法的三次贝塞尔曲线的系数值")
    if coef.shape == (2,2): coef = np.stack([coef.T[0],coef.T[1],[0,0],[0,0]],axis=1)
    if coef.shape == (2,3): coef = np.stack([coef.T[0],coef.T[1],coef.T[2],[0,0]],axis=1)
    return coef

def ctrls_to_coef(*ctrls):
    '''支持二个或者四个控制点'''
    ctrls = [to_xy(ctrl) for ctrl in ctrls]
    P = np.stack(ctrls,axis=1)
    match len(ctrls):
        case 2:
            A = np.array([[1,-1],
                          [0, 1]])
            C =  np.dot(P,A)
            return np.block([[C[0],0,0],[C[1],0,0]])
        case 4:
            A = np.array([[1,-3,3,-1],
                          [0,3,-6,3],
                          [0,0,3,-3],
                          [0,0,0, 1]])
            return np.dot(P,A)
        case _:
            raise ValueError(f"长度为{len(ctrls)}的控制点序列暂不支持，只支持2,4")
    
def segment_to_coefs(segment):
    '''将segment转为控制点序列的序列,(N,2,4)'''
    for seg in segment:
        coeficients = []
        for seg in segment:
            match seg[0]:
                case "line":
                    for i in range(1,len(seg)-1):
                        coeficients.append(ctrls_to_coef(*seg[i:i+2]))
                case "cubic":
                    coeficients.append(ctrls_to_coef(seg[1],seg[3],seg[4],seg[2]))
                case _:
                    raise ValueError(f"{seg[0]}不是支持的segment类型")
        return np.array(coeficients,dtype=float)

def coefs_to_center(coefs):
        '''请保证你的路径闭合,coefs:(N,2,4)'''
        area = 0 
        intX = 0
        intY = 0
        for co in coefs:
            x_t,y_t = np.polynomial.Polynomial(co[0]),np.polynomial.Polynomial(co[1])
            dx_t,dy_t = x_t.deriv(1),y_t.deriv(1)
            area += quad(lambda t: y_t(t)*dx_t(t)+ 2*x_t(t)*dy_t(t) , 0,1)[0] 
            intX += quad(lambda t: x_t(t)**2*dy_t(t),0,1)[0]/2
            intY += quad(lambda t: -y_t(t)**2*dx_t(t),0,1)[0]/2
        return intX/area,intY/area

def coefs_to_length_and_nodeweight(coefs):
    lengths = []
    error = 0
    for c in coefs:
        dx_t = np.polynomial.Polynomial(c[0]).deriv(1)
        dy_t = np.polynomial.Polynomial(c[1]).deriv(1)
        r = quad(lambda t : np.sqrt((dx_t(t) ** 2 + dy_t(t) ** 2)),0,1)
        error += r[1]
        lengths.append(r[0])
    lengths = np.array(lengths)
    L = lengths.sum()
    nodeweights = []
    for i in range(1,len(lengths)+1):
        nodeweights.append(lengths[:i].sum())
    nodeweights = [nw/L for nw in nodeweights]
    return L , nodeweights,error

def get_bezier_point(coef,t):
    assert 0 <= t <= 1
    x_t,y_t = np.polynomial.Polynomial(coef=coef[0]),np.polynomial.Polynomial(coef=coef[1])
    return to_xy((x_t(t),y_t(t)))

def bezier_line_intersection(bezier_coef,line_point,line_vect):
    line_point,line_vect = to_xy(line_point),to_xy(line_vect)
    bezier_coef = check_bezier_coef(bezier_coef)
    X0,Y0 = np.array([line_point[0],0,0,0]),np.array([line_point[1],0,0,0])
    An = line_vect[1] * (bezier_coef[0] - X0) - line_vect[0] * (bezier_coef[1] - Y0)
    #
    #An = np.array([0,-1/4,0,1],dtype=float)
    result = []
    if (An == 0).all(): raise ValueError("无穷解，输入参数是两条重合直线") 
    elif (An[1:] == 0).all() : pass # 无解，两条平行线
    elif (An[2:] == 0).all(): # 一次多项式
        r = - An[0]/An[1]
        result.append(r)
    elif (An[3:] == 0).all(): # 二次多项式
        c,b,a = An[:3]
        Delta = b^2 - 4 * a * c 
        if Delta == 0 : 
            r = - b/(2*a)
            result.append(r)
        elif Delta < 0 : pass 
        else : 
            r1,r2 = - b/(2*a) + np.sqrt(Delta) , -b/(2*a) + np.sqrt(Delta)
            result.extend([r1,r2])
    else: # 三次多项式
        p = (3*An[3]*An[1] - An[2]**2)/(3*An[3]**2)
        q = (27* An[3]**2 * An[0] - 9 * An[3]*An[2]*An[1] + 2 * An[2]**3) / (27 * An[3]**3)
        d =  - An[2]/(3*An[3])
        Delta = (q / 2)**2 + (p/3) ** 3 
        if Delta > 0 : #一实根
            r = np.power(-q/2 + np.sqrt(Delta),1/3) +  np.power(-q/2 - np.sqrt(Delta),1/3)
            result.append(r)
        elif Delta == 0 : # 1实根或者2实根
            if q == 0 and p == 0: r = 0 
            else:
                r1,r2 = np.power(- q/2 , 1/3), 2 * np.power(-q/2,1/3)
                result.extend([r1,r2])
        else: # 三实根 
            radius = np.power(-(p/3)**3,1/2)
            theta = 1/3 * np.arccos(- q/(2*radius))
            radius = 2 * np.power(radius,1/3)
            r1,r2,r3 = d + radius * np.cos(theta) , d + radius * np.cos(theta + 2/3*np.pi) , d + radius * np.cos(theta + 4/3*np.pi)
            result.extend([r1,r2,r3])
        '''F_t = np.polynomial.Polynomial(An)
        rs = F_t.roots()
        result.extend(rs)'''
    _result = []
    for r in result:
        if len(result) != 0  and (not np.isclose(r,_result).any()):
            _result.append(r)
    result = []
    for r in _result:
        if np.isclose(r,0) or np.isclose(1 - r,0) or 0 < r < 1:
            result.append(r)
    x_t,y_t = np.polynomial.Polynomial(bezier_coef[0]),np.polynomial.Polynomial(bezier_coef[1])
    points = [(x_t(t),y_t(t)) for t in result]
    return np.array(points,dtype=float)
#!
def bezier_bezier_intersection():
    pass 





if __name__ == '__main__':
    print(bezier_line_intersection(
        segment_to_coefs(
            [
                ("cubic",(0,0),(10,4),(5,0),(5,4))
            ]
        )[0],
        line_point=(0,4),
        line_vect=(10,-4)
    ))