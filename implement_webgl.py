import re

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Remove old basic webgl code block to clean up the workspace
html = re.sub(r'<!-- WEBGL -->.*?</body>', '</body>', html, flags=re.DOTALL)

webgl_script = """<!-- WEBGL GLASS SYSTEM -->
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
        uniform float uCardRects[200]; // MAX_CARDS * 4
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

        vec3 sampleBgBlurred(vec2 uv, float radius) {
            if (radius < 0.5) return sampleBg(uv);
            vec3 sum = vec3(0.0);
            vec2 px = 1.0 / uResolution;
            vec2 offsets[16];
            offsets[0]  = vec2(-0.94201, -0.39906); offsets[1]  = vec2( 0.94558, -0.76890);
            offsets[2]  = vec2(-0.09418, -0.92938); offsets[3]  = vec2( 0.34495,  0.29387);
            offsets[4]  = vec2(-0.91588, -0.45771); offsets[5]  = vec2(-0.81544,  0.48568);
            offsets[6]  = vec2(-0.38277, -0.56071); offsets[7]  = vec2(-0.12675,  0.84686);
            offsets[8]  = vec2( 0.89642,  0.41254); offsets[9]  = vec2( 0.18150, -0.30020);
            offsets[10] = vec2(-0.01445, -0.16001); offsets[11] = vec2( 0.59614,  0.71118);
            offsets[12] = vec2( 0.49742, -0.47280); offsets[13] = vec2( 0.80685,  0.04588);
            offsets[14] = vec2(-0.32490, -0.03965); offsets[15] = vec2(-0.60975,  0.06566);
            for (int i = 0; i < 16; i++) {
                sum += sampleBg(uv + offsets[i] * radius * px);
            }
            return sum / 16.0;
        }

        float surfaceHeight(float t) {
            float s = 1.0 - t;
            return pow(1.0 - s*s*s*s, 0.25);
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

            if (!inside && minDist > 15.0) discard;

            if (!inside) {
                // Smooth Arc-style drop shadow
                float shadowFalloff = exp(-minDist * minDist / 200.0);
                gl_FragColor = vec4(0.0, 0.0, 0.0, 0.4 * shadowFalloff);
                return;
            }

            // Real refraction IOR logic matching the webgl.html
            float distFromEdge = -minDist;
            float bezel = min(40.0, min(closestHalfSize.x, closestHalfSize.y) - 1.0);
            float t = clamp(distFromEdge / bezel, 0.0, 1.0);
            
            float h = surfaceHeight(t);
            float dt = 0.001;
            float h2 = surfaceHeight(min(t + dt, 1.0));
            float dh = (h2 - h) / dt;

            // IOR Based distortion setup
            float uThickness = 50.0;
            float uIOR = 2.5; // Premium refraction ratio
            float slopeAngle = atan(dh * (uThickness / bezel));
            float sinR = clamp(sin(slopeAngle) / uIOR, -1.0, 1.0);
            float thetaR = asin(sinR);
            float displacement = h * uThickness * (tan(slopeAngle) - tan(thetaR));

            // Gradient / curvature
            float eps = 0.5;
            vec2 grad;
            grad.x = sdRoundedRect((screenPx - closestCenter) + vec2(eps, 0.0), closestHalfSize, uRadius) - minDist;
            grad.y = sdRoundedRect((screenPx - closestCenter) + vec2(0.0, eps), closestHalfSize, uRadius) - minDist;
            grad = normalize(grad);

            vec2 offset = -grad * displacement / uResolution;
            vec2 screenUV = screenPx / uResolution;
            
            // Chromatic aberration (slight channel offsets matching premium feel)
            float chroma = 0.006 * displacement;
            vec2 refractedUV_R = screenUV + offset * (1.0 + chroma);
            vec2 refractedUV_G = screenUV + offset;
            vec2 refractedUV_B = screenUV + offset * (1.0 - chroma);
            
            vec3 color;
            float uBlur = 1.5;
            color.r = sampleBgBlurred(refractedUV_R, uBlur).r;
            color.g = sampleBgBlurred(refractedUV_G, uBlur).g;
            color.b = sampleBgBlurred(refractedUV_B, uBlur).b;
            
            // Rim Light (Soft specular highlight)
            vec2 lightDir = normalize(vec2(0.5, -0.7));
            float rimDot = abs(dot(grad, lightDir));
            float rimFalloff = 1.0 - smoothstep(0.0, bezel * 0.4, distFromEdge);
            float specHighlight = pow(rimDot * rimFalloff, 1.5);
            color += vec3(specHighlight * 0.4);

            // Inner Shadow for depth
            float innerShadow = 1.0 - smoothstep(0.0, bezel * 0.6, distFromEdge);
            color *= mix(1.0, 0.7, innerShadow * 0.3);

            // Inner Rim
            float innerRim = smoothstep(0.0, 2.0, distFromEdge) * (1.0 - smoothstep(2.0, 5.0, distFromEdge));
            color += vec3(innerRim * 0.1 * 0.4);

            // Subtly tint towards restraint Aurora colors
            color = mix(color, vec3(0.08, 0.11, 0.18), 0.15); // Aurora blue tint
            
            // Maintain translucency fade at edges 
            float alpha = smoothstep(0.0, 1.5, distFromEdge);
            gl_FragColor = vec4(color, alpha);
        }
    `;

    const material = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms,
        transparent: true,
        depthTest: false
    });

    const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    scene.add(plane);

    const updateWebGL = () => {
        // Continuous sync array 
        const cards = document.querySelectorAll('.tcard');
        let count = 0;
        cards.forEach((card, i) => {
            if (i >= MAX_CARDS) return;
            // Native smooth layout changes during drag via standard offset syncs real-time
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
</body>"""

html = html.replace('</body>', webgl_script)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("WebGL Implementation integrated.")
