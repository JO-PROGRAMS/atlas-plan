with open('index.html', 'r') as f:
    c = f.read()

target = """        uRadius: { value: 24.0 }, 
        uBgTex: { value: null },
        uBgAspect: { value: 1.5 }
    };

    new THREE.TextureLoader().load('assets/default.avif', (tex) => {
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        uniforms.uBgTex.value = tex;
        uniforms.uBgAspect.value = tex.image.width / tex.image.height;
    });"""

replacement = """        uRadius: { value: 24.0 }, 
        uBgTex: { value: null },
        uBgAspect: { value: 1.5 },
        uHasTex: { value: 0 }
    };

    // Robust Fallback anvas Texture
    const fallbackCanvas = document.createElement('canvas');
    fallbackCanvas.width = 1024;
    fallbackCanvas.height = 1024;
    const fctx = fallbackCanvas.getContext('2d');
    
    // Create a beautiful premium mesh gradient matching Claude/Arc styles
    const gradient = fctx.createLinearGradient(0, 0, 1024, 1024);
    gradient.addColorStop(0, '#1c2841'); // Deep aur    c = f.read()

target = """   p(
target = """  ; /        uBgTex: { value: null },
        uBgA'#        uBgAspect: { value: 1.5di    };

    new THREE.TextureLoa  
    se         tex.minFilter = THREE.LinearFilter;
        tex.magFilter =02 );
    
    // Add some soft glowing orbs
         unrawOrb = (x, y, r, color) => {
           uniforms.uBgAspect.value = ia    });"""

replacement = """        uRadius: { value: 24.0 }, 
       
replacemGra        uBgTex: { value: null },
        uBgAspectil        uBgAspect: { value: 1.5be        uHasTex: { value: 0 }
    r    };

    // Robust Fallbact
    l()    const fallbackCanvas = document.'r    fallbackCanvas.width = 1024;
    fallbackCanvas.height a(    fallbackCanvas.height = 102aw    const fctx = fallbackCanvas.,     
    // Create a beautiflbackTex = new THREE.C   as    const gradient = fctx.createLinearGradient(0, 0, 1024, 1024);
    gra     allbackTex.magFilter = THREE.LinearFilter;
    uniforms.uBgTex.value = fallbackTex;
    uniforms.uBgAspect.value = 1.0;
    uniforms.target = """  ; 1;        uBgA'#        uBgAspect: { value: 1.5di au
    new THREE.TextureLoa  
    se         tex.minFiine    se         tex.minFilFi        tex.magFilter =02 );
    
    // Add somex.    
    // Add some soft gms   gA         unrawOrb = (x, y, r, c te           uniforms.uBgAspect.value = ia{

replacement = """        uRadius: { value: 24.0 mag       
replacemGra        uBgTex: { value: null }f replac i        uBgAspectil        uBgAspect: { va:
    r    };

    // Robust Fallbact
    l()    const fallbackCanvas = document.'ri
