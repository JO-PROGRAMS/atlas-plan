import re

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

new_css_vars = """  --font-ui: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
  --font-accent: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
  --bg: #09090b;
  --bg1: #18181b;
  --bg2: #27272a;"""
html = re.sub(r"--font-ui:[^;]*;.*?--bg2:[^;]*;", new_css_vars, html, flags=re.DOTALL)

noise_css = """
body {
  background: var(--bg);
  color: var(--t1);
}
#noise {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.04;
  background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
}
#webgl-canvas {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  pointer-events: none;
  z-index: -1;
}
#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: url('assets/default.avif') center/cover no-repeat;
  z-index: -2;
}
.tcard {
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
}
.tcard::before, .tcard::after { display: none !important; }
"""
if '<style>' in html:
    html = html.replace('<style>', '<style>\n' + noise_css + '\n')

if '<body>' in html:
    html = html.replace('<body>', '<body>\n  <div id="bg-layer"></div>\n  <canvas id="webgl-canvas"></canvas>\n  <div id="noise"></div>\n')

webgl_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
window.addEventListener('load', () => {
    const canvas = document.getElementById('webgl-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const MAX_CARDS = 50;
    const uniforms = {
        uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
        uCardRects: { value: new Float32Array(MAX_CARDS * 4) },
        uCardCount: { value: 0 },
        uRadius: { value: 24.0 },
        uBgTex: { value: null },
        uBgAspect: { value: 1.5 }
    };

    new THREE.TextureLoader().load('assets/default.avif', (tex) => {
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        uniforms.uBgTex.value = tex;
        uniforms.uBgAspect.value = tex.image.width / tex.image.height;
    });

    const vertexShader = `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = vec4(position, 1.0);
        }
    `;

    const fragmentShader = `
        precision highp float;
        varying vec2 vUv;

        uniform vec2 uResolution;
        uniform float uCardRects[200];
        uniform int uCardCount;
        uniform float uRadius;
        uniform sampler2D uBgTex;
        uniform float uBgAspect;

        float sdRoundedRect(vec2 p, vec2 halfSize, float r) {
            vec2 q = abs(p) - halfSize + r;
            return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
        }

        vec3 sampleBg(vec2 screenUV) {
            float screenAspect = uResolution.x / uResolution.y;
            vec2 uv = screenUV;
            if (uBgAspect > screenAspect) {
                float s = screenAspect / uBgAspect;
                uv.x = uv.x * s + (1.0 - s) * 0.5;
            } else {
                float s = uBgAspect / screenAspect;
                uv.y = uv.y * s + (1.0 - s) * 0.5;
            }
            uv.y = 1.0 - uv.y;
            return texture2D(uBgTex, uv).rgb;
        }

        void main() {
            vec2 screenPx = vec2(vUv.x, 1.0 - vUv.y) * uResolution;
            
            float minDist = 9999.0;
            vec2 closestCenter = vec2(0.0);
            vec2 closestHalfSize = vec2(0.0);
            bool inside = false;

            for(int i=0; i<50; i++) {
                if(i >= uCardCount) break;
                float cx = uCardRects[i*4 + 0];
                float cy = uCardRects[i*4 + 1];
                float w  = uCardRects[i*4 + 2];
                float h  = uCardRects[i*4 + 3];

                vec2 center = vec2(cx + w/2.0, cy + h/2.0);
                vec2 halfSize = vec2(w/2.0, h/2.0);

                float sd = sdRoundedRect(screenPx - center, halfSize, uRadius);
                if (sd < minDist) {
                    minDist = sd;
                    closestCenter = center;
                    closestHalfSize = halfSize;
                }
                if (sd <= 0.0) {
                    inside = true;
                }
            }

            if (!inside && minDist > 20.0) {
                discard;
            }

            if (!inside) {
                float shadowFalloff = exp(-minDist * minDist / 800.0);
                gl_FragColor = vec4(0.0, 0.0, 0.0, 0.5 * shadowFalloff);
                return;
            }

            float distFromEdge = -minDist;
            float bezel = 40.0;
            float t = clamp(distFromEdge / bezel, 0.0, 1.0);
            
            float hHeight = pow(1.0 - (1.0-t)*(1.0-t)*(1.0-t)*(1.0-t), 0.25);
            vec2 p = screenPx - closestCenter;
            
            float eps = 1.0;
            vec2 grad;
            grad.x = sdRoundedRect(p + vec2(eps, 0.0), closestHalfSize, uRadius) - minDist;
            grad.y = sdRoundedRect(p + vec2(0.0, eps), closestHalfSize, uRadius) - minDist;
            grad = normalize(grad);

            vec2 offset = -grad * hHeight * 30.0 / uResolution;
            vec2 refractedUV = (screenPx / uResolution) + offset;
            
            vec3 color = sampleBg(refractedUV);
            
            vec2 lightDir = normalize(vec2(0.5, -0.8));
            float rimDot = abs(dot(grad, lightDir));
            float rimFalloff = 1.0 - smoothstep(0.0, bezel * 0.4, distFromEdge);
            float spec = pow(rimDot * rimFalloff, 2.0) * 0.4;
            color += vec3(spec);

            float innerShadow = 1.0 - smoothstep(0.0, bezel * 0.6, distFromEdge);
            color *= mix(1.0, 0.7, innerShadow * 0.3);

            color = mix(color, vec3(1.0, 1.0, 1.0), 0.08);

            gl_FragColor = vec4(color, 1.0);
        }
    `;

    const material = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms,
        transparent: true
    });

    const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    scene.add(plane);

    const updateWebGL = () => {
        const cards = document.querySelectorAll('.tcard:not(.reordering)');
        let count = 0;
        cards.forEach((card, i) => {
            if (i >= MAX_CARDS) return;
            const rect = card.getBoundingClientRect();
            uniforms.uCardRects.value[i * 4 + 0] = rect.left;
            uniforms.uCardRects.value[i * 4 + 1] = rect.top;
            uniforms.uCardRects.value[i * 4 + 2] = rect.width;
            uniforms.uCardRects.value[i * 4 + 3] = rect.height;
            count++;
        });
        uniforms.uCardCount.value = count;
        renderer.render(scene, camera);
        requestAnimationFrame(updateWebGL);
    };
    requestAnimationFrame(updateWebGL);

    window.addEventListener('resize', () => {
        renderer.setSize(window.innerWidth, window.innerHeight);
        uniforms.uResolution.value.set(window.innerWidth, window.innerHeight);
    });
});
</script>
"""

if '<!-- WEBGL -->' not in html:
    html = html.replace('</body>', '<!-- WEBGL -->\n' + webgl_script + '\n</body>')

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Injected WebGL Multi-Card Glass Effect successfully.")
