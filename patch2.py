import re

with open('index.html', 'r') as f:
    text = f.read()

pattern = r"uBgTex: \{ value: null \},\s*uBgAspect: \{ value: 1\.5 \}\s*\};\s*new THREE\.TextureLoader\(\)\.load\('assets/default\.avif', \(tex\) => \{\s*tex\.minFilter = THREE\.LinearFilter;\s*tex\.magFilter = THREE\.LinearFilter;\s*uniforms\.uBgTex\.value = tex;\s*uniforms\.uBgAspect\.value = tex\.image\.width / tex\.image\.height;\s*\}\);"

replacement = """uBgTex: { value: null },
        uBgAspect: { value: 1.5 }
    };

    // Robust Fallback Canvas Texture
    const fallbackCanvas = document.createElement('canvas');
    fallbackCanvas.width = 1024;
    fallbackCanvas.height = 1024;
    const fctx = fallbackCanvas.getContext('2d');
    
    // Create a beautiful premium mesh gradient matching Claude/Arc styles
    const gradient = fctx.createLinearGradient(0, 0, 1024, 1024);
    gradient.addColorStop(0, '#1c2841'); // Deep aurora blue
    gradient.addColorStop(0.4, '#2d1e3d'); // Subtle plum
    gradient.addColorStop(0.7, '#16233a'); // Dark ocean
    gradient.addColorStop(1, '#0f1423');   // Base void
    fctx.fillStyle = gradient;
    fctx.fillRect(0, 0, 1024, 1024);
    
    // Add some soft glowing orbs
    const drawOrb = (x, y, r, color) => {
        const radGrad = fctx.createRadialGradient(x, y, 0, x, y, r);
        radGrad.addColorStop(0, color);
        radGrad.addColorStop(1, 'rgba(0,0,0,0)');
        fctx.fillStyle = radGrad;
        fctx.beginPath();
        fctx.arc(x, y, r, 0, Math.PI * 2);
        fctx.fill();
    };
    drawOrb(200, 300, 600, 'rgba(100, 150, 255, 0.3)'); 
    drawOrb(800, 800, 700, 'rgba(235, 100, 160, 0.25)'); 
    drawOrb(800, 100, 500, 'rgba(50, 200, 200, 0.3)'); 

    const fallbackTex = new THREE.CanvasTexture(fallbackCanvas);
    fallbackTex.minFilter = THREE.LinearFilter;
    fallbackTex.magFilter = THREE.LinearFilter;
    uniforms.uBgTex.value = fallbackTex;
    uniforms.uBgAspect.value = 1.0;

    new THREE.TextureLoader().load('assets/default.avif', (tex) => {
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        uniforms.uBgTex.value = tex;
        uniforms.uBgAspect.value = tex.image.width / tex.image.height;
    }, undefined, () => {
        console.warn('Could not load background image, using premium procedural gradient.');
    });"""

new_text, count = re.subn(pattern, replacement, text)

if count > 0:
    with open('index.html', 'w') as f:
        f.write(new_text)
    print("Successfully replaced texture loader logic!")
else:
    print("Could not find the target string!")