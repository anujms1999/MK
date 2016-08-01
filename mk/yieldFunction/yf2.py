### yf version that relies on fortran version of yield functions
import matplotlib as mpl
import os
mpl_backend=mpl.get_backend()
print 'mpl.backend:',mpl_backend

from MP.lib import whichcomp
submitCommand, availX = whichcomp.determineEnvironment()
if not(availX): mpl.use('Agg') ## In case X-window is not available.

from yf_for import vm, hqe, hill48
import yf_yld2000 as yld2000
#from .. import library
from mk.library.lib import c6p, c2s6, rotPrincOrig, gen_tempfile  ## cauchy stress to principal stresses
import numpy as np

def wrapYLD_SA(r=[1,1,1,1],y=[1,1,1,1],m=6):
    """
    Running yld2000_sa (stand-alone) executable to deal with
    the unwanted stop while estimating yld2000-2d coefficieints

    Arguments
    ---------
    r=[1,1,1,1]
    y=[1,1,1,1]
    m=6
    """
    import yf_yld2000
    path = os.path.split(yf_yld2000.__file__)[0]
    cmd = os.path.join(path,'yld2000_sa')
    for i in xrange(4):
        cmd = '%s %.5e'%(cmd, y[i])
    for i in xrange(4):
        cmd = '%s %.5e'%(cmd, r[i])
    cmd = '%s %.5e'%(cmd, m)
    ## append file name
    fnTemp = gen_tempfile(prefix='yld2000-sa',ext='tmp',affix='la')
    cmd = '%s %s'%(cmd,fnTemp)
    cmd = '%s > /tmp/dump'%cmd
    # print cmd
    flag = os.system(cmd)
    # print flag

    if flag==0:
        ## read la
        la = yld2000.readla(fnTemp)
        return la
    else:
        return -1 ## fail to converge
    raise IOError, 'unexpected case'

def wrapYLD(r=[1,1,1,1],y=[1,1,1,1],m=6,k=2):
    """
    Gvien 8 parameteres
    characterize yld2000-2d and return the outputs...

    Arguments
    ---------
    r=[1,1,1,1]   ## r-values
    y=[1,1,1,1]   ## yield stresses
    m=6           ## exponent
    k=2
    """
    import time
    r, y = np.array(r),np.array(y)
    ac=np.concatenate((y,r),axis=0)
    ##
    t0=time.time()

    nit = 100
    iexit=False
    l = wrapYLD_SA(r=r,y=y,m=m)
    # print 'elapsed time for characterizing yld2000-2d:',\
    #     time.time()-t0
    if type(l).__name__=='int':
        ## return bogus results?
        return l
    else:
        ##
        def yld_func(s):
            #         s, e, f,   e1,  f1,   de1 = yld2000.skew(m,k,l,s)
            # newstress, e, h, phi, dphi ,d2phi = yld2000.skew(m,k,l,s) -old
            newstress  , e, h, dphi, phi, d2phi =  yld2000.skew(m,k,l,s)
            return newstress, phi, dphi,d2phi
    return yld_func

def VonMises(s):
    """
    Wrapper of Von Mises yield function (no parameter is required)

    Argument
    --------
    s
    """
    snew,phi,dphi,d2phi = vm(s)
    return snew,phi,dphi,d2phi

def wrapHill48Gen(f,g,h,n):
    """
    Given 4 parameters (for plane-stress condition),
    characterize Hill48 yield function and returns
    the outputs generated by Hill48 function

    Arguments
    ---------
    f
    g
    h
    n
    """
    def func(s):
        return  Hill48(s,f,g,h,n)
    return func

def wrapHill48R(rvs):
    """
    This wrapper gives Hill48 yield function that is
    characterized by r-values. R-values are passed as
    list (or numpy array) and is supposed to be a collection
    measured at an equi-angle interval from RD to TD.
    For example, when rvs=[1.5, 2.0] is given, it is assumed
    that the corresponding r-values are 1.5 and 2.0 at RD and TD.

    When the argument is a list that has 3 elements, it is assumed
    that each element is an r-value measured at, 0, 45 and 90 degrees
    from RD.

    Hill48 using r-values

    Argument
    --------
    rvs
    """
    import tuneH48
    Hill48params = tuneH48.tuneGenR(rvs)
    f,g,h,n=Hill48params
    return wrapHill48Gen(f,g,h,n)

def wrapHill48Y(ys,r0=None,r90=None):
    """
    This wrapper gives Hill48 yield function that is
    characterized by in-plane uniaxial yield stresses and an r-value (either r0 or r90).
    Yield stresses are passed as a list variable (or numpy array)
    and is supposed to be a collection measured at an equi-angle
    interval from RD to TD. For example, when ys=[1.5, 2.0] is given,
    it is assumed that the corresponding yield stresses are 1.5 and 2.0 at RD and TD.

    When the argument is a list that has 3 elements, it is assumed
    that each element is an yield stress measured at, 0, 45 and 90 degrees
    from RD, respectively.

    Hill48 using yield-stresses

    Arguments
    ---------
    ys
    r0
    r90
    """
    import tuneH48
    Hill48params = tuneH48.tuneGenY(y=ys,r0=r0,r90=r90)
    f,g,h,n=Hill48params
    return wrapHill48Gen(f,g,h,n)

def wrapHill48(r0,r90):
    """
    Wrapper of Hill48 yield function that is characterized by two r-values

    This is a wrapper of Hill48 but is characterized by the Hill's
    quadratic yield function for plane stress that accepts only two r-values
    (i.e., R0 and R90.)

    What this function does is:
     1) plot yield locus of Hill quadratic

    """
    import tuneH48
    Hill48params = tuneH48.tuneR2(r0=r0,r90=r90) ## tune based on r0 and r90
    f, g, h, n = Hill48params
    return wrapHill48Gen(f,g,h,n)

def Hill48(s,f,g,h,n):
    """
    Arguments
    ---------
    s    :6d-stress
    f,g,h,n: Hill parameters for the case of plane-stress space
    """
    snew,phi,dphi,d2phi = hill48(s,f,g,h,n)
    return snew, phi, dphi, d2phi

def wrapHillQuad(r0,r90):
    def func(s):
       return HillQuad(s,r0,r90)
    return func

def HillQuad(s=None,r0=2.0,r90=2.3):
    """
    Arguments
    ---------
    s    : 6d stress    (it should be referenced in the material axes)
                               axis1//RD, axi2//TD
    r0   : r-value along 0
    r90  : r-value along 90
    """
    ## incomplete here - axis1 // rd, it should be such that axis 2 // td
    ## This, in the current form, may not enforce axis 1 to e aligned with RD
    ##
    srd = s[0]; std = s[1]
    if srd>=std:  pdir = 'rd'
    elif srd<std: pdir = 'td'

    princStress,rotMatrix = c6p(s)
    sPrinc,phi,dphi,d2phi = hqe(s=princStress,r0=r0,r90=r90) ## principal values

    s33    = rotPrincOrig(rotMatrix,sPrinc)
    snew   = c2s6(s33)
    dphi33 = rotPrincOrig(rotMatrix,dphi)
    dphi   = c2s6(dphi33)

    # d2phi = np.dot(rotMatrix,dphi)  - need to define d2phi in 'for.f' first.
    return snew,phi,dphi,d2phi

def test3():
    """
    """
    import vm_check
    vm_check.main()

def test2(r0=2.20,r45=1.95,r90=2.9):
    """
    uniaxial tension tests

    Arguments
    ---------
    r0  =2.1
    r90 =2.7
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from mk.library.lib import rot
    import numpy as np
    from mk.tests.mechtests import inplaneTension
    h48 = wrapHill48R([r0,r45,r90])

    psis = np.linspace(0,+np.pi/2.,100)
    ## uniaxial tension stress state in the laboratory axes
    sUniaxial=np.zeros(6)
    sUniaxial[0]=1.

    print '%6s %6s %6s %6s %6s %6s %6s %6s'%(
        'th','phi','s11','s22','s12','s1','s2','s3')
    psis, rvs, phis = inplaneTension(fYLD=h48)

    fig = plt.figure(figsize=(10,3))
    ax1  = fig.add_subplot(131)
    ax2  = fig.add_subplot(132)
    ax3  = fig.add_subplot(133)
    import vm_check
    ax2.plot(psis*180/np.pi,rvs)
    ax3.plot(psis*180/np.pi,phis)
    vm_check.main(ax=ax1)
    ax2.set_ylabel(r'R value')
    ax3.set_ylabel(r'$\Phi$')
    fig.tight_layout()

    for ax in [ax2,ax3]:
        ax.set_xlabel(r'$\theta$ [deg] from RD')
        ax.set_xticks(np.arange(0,90.001,30))

    fn = 'yf2_test2.pdf'
    fig.savefig(fn,bbox_inches='tight')
    print '%s has been saved'%fn

def test1():
    import mk.materials.materials
    s1  = [1.,0.,0.,0.,0.,0.] ## uniaxial s11
    s2  = [0.,1.,0.,0.,0.,0.] ## uniaxial s22
    s3  = [0.,0.,0.,0.,0.,1.] ## uniaxial s12
    s4  = [1.,1.,0.,0.,0.,0.] ## uniaxial balanced biaxial
    s5  = [1.,-1.,0.,0.,0.,0.] ## pure shear1
    s6  = [-1.,1.,0.,0.,0.,0.] ## pure shear2


    ss = [s1,s2,s3,s4,s5,s6]
    r0 =1.; r90=1.

    iopts = [0,1,2,3,4,5]
    mats=[]
    for i in xrange(len(iopts)):
        mats.append(mk.materials.materials.library(i))

    coords=np.zeros((len(mats),len(ss),3))
    for j in xrange(len(mats)):
        for i in xrange(len(ss)):
            # snew, phi, dphi, d2phi = HillQuad(s=ss[i],r0=r0,r90=1.)
            mat = mats[j]()
            snew,phi,dphi,d2phi = mat.f_yld(ss[i])
            s11, s22, s12 = snew[0],snew[1],snew[5]
            coords[j,i,:] = s11,s22,s12

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure()
    ax  = fig.add_subplot(111,projection='3d')

    colors=['r','g','b','m','c','y','k']
    for j in xrange(len(mats)):
        x,y,z = coords[j,:,0],coords[j,:,1],coords[j,:,2]
        ax.scatter(x,y,z,color=colors[j])

    ax.set_xlabel(r'$\sigma_{11}$')
    ax.set_ylabel(r'$\sigma_{22}$')
    ax.set_zlabel(r'$\sigma_{12}$')
    ax.set_aspect('equal')

    fn ='yf2_test1.pdf'
    fig.savefig(fn)
    print '%s has been saved'%fn

if __name__=='__main__':
    # test1()
    test2() # - uniaxial tension along various directions - not working yet
    #test3()
