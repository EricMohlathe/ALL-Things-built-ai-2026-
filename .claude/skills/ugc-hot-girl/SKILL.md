---
name: ugc-hot-girl
description: Generate a detailed AI image prompt for creating an attractive female UGC ad character. Use when the user wants to create a "hot girl" character image for UGC ads, influencer-style content, product testimonials, or social media ad creatives. Triggers on requests like "create a UGC girl", "hot girl for ads", "female influencer image", "UGC character", "testimonial girl", or any request for a female character for ad/UGC content.
---

# UGC Hot Girl — Character Image Prompt Generator

This skill turns Claude into a specialized prompt engineer for creating photorealistic, attractive female characters optimized for UGC (User-Generated Content) ad videos. The output is a paste-ready image generation prompt for Higgsfield Soul 2.0 or Nano Banana Pro.

---

## What This Skill Does

When invoked, Claude will:

1. Ask the user about their UGC ad context (product, vibe, platform, ethnicity preference, age range)
2. Generate a **detailed, production-grade image prompt** optimized for Soul 2.0
3. The resulting image is designed to look like a real person — not AI-generated — for maximum UGC authenticity

If the user provides no specifics, generate a versatile, broadly appealing character suitable for general product testimonials.

---

## Prompt Engineering Framework

### Core Principles

1. **Authenticity over perfection** — UGC works because it looks real. Avoid overly polished, magazine-cover looks. Aim for "naturally attractive person you'd see on TikTok"
2. **Camera-aware expression** — The character should look like they're about to speak to camera. Slight smile, engaged eyes, mid-conversation energy
3. **Lighting that sells** — Golden hour, ring light, or natural window light. These are the lighting setups real UGC creators use
4. **Platform-native styling** — Casual, trendy clothing that matches the target platform (TikTok, Instagram, YouTube)

### Prompt Structure

Every prompt should include these layers in order:

```
[Subject Description] + [Age & Features] + [Expression & Pose] + [Clothing & Style] + [Lighting] + [Camera & Framing] + [Background] + [Technical Quality]
```

### Subject Description Elements

**Age ranges** (pick based on product/audience):
- Gen Z (18-24): Fresh, trendy, social-media-native look
- Young professional (25-30): Polished but approachable
- Millennial (28-35): Relatable, established, trustworthy

**Skin & features** (always specify for consistency):
- Skin texture: "natural skin texture with subtle pores", "realistic skin with light freckles"
- Avoid: "perfect", "flawless", "porcelain" — these trigger AI-looking results
- Include: "healthy glow", "natural complexion", "sun-kissed"

**Hair** (keeps character recognizable across generations):
- Specify color, length, texture, and style
- "Loose beach waves", "straight with subtle layers", "natural curls"
- Messy/effortless styles read more authentic than salon-perfect

### Expression & Energy

**For testimonial/talking-head UGC:**
- "Mid-conversation expression, slightly raised eyebrows, genuine smile"
- "Looking directly at camera with warm, engaged eyes"
- "Slight head tilt, about to speak, natural and relaxed"
- "Animated expression, one hand gesturing near face"

**For product showcase UGC:**
- "Looking at product with genuine interest and slight smile"
- "Holding product near face, excited expression"
- "Surprised/delighted reaction, mouth slightly open"

**For lifestyle UGC:**
- "Candid laugh, looking slightly off-camera"
- "Relaxed pose, comfortable in their environment"
- "Natural movement, caught mid-action"

### Clothing & Styling

**Casual/everyday (most versatile):**
- White crop top, oversized tee, tank top
- Minimal jewelry (small hoops, thin necklace)
- Natural/minimal makeup look

**Elevated casual (beauty/fashion products):**
- Trendy basics, neutral tones
- Statement earrings or layered necklaces
- Soft glam makeup

**Athleisure (fitness/wellness products):**
- Sports bra, workout set, yoga wear
- Hair pulled back, post-workout glow
- No makeup / dewy skin

### Lighting Setups

| Setup | When to Use | Prompt Phrasing |
|---|---|---|
| Golden hour | Most versatile, warm & flattering | "warm golden hour sunlight, soft directional light from the side" |
| Ring light | Beauty/skincare products | "soft ring light illumination, even facial lighting, catchlights in eyes" |
| Window light | Indoor testimonials | "soft natural window light from the left, gentle shadows" |
| Overcast outdoor | Lifestyle/casual | "soft diffused outdoor lighting, no harsh shadows" |

### Camera & Framing

**For UGC talking-head videos:**
- "Close-up portrait, head and shoulders, shot on iPhone"
- "Selfie angle, slightly above eye level, 26mm lens"
- "Medium close-up, chest up, shallow depth of field f/1.8"

**For product showcase:**
- "Medium shot, waist up, product visible in hands"
- "Close-up with product held near face"

### Background

**Keep it simple and UGC-authentic:**
- "Clean neutral background, slightly blurred"
- "Minimalist bedroom/apartment setting, soft bokeh"
- "Outdoor cafe, shallow depth of field"
- "Bathroom mirror selfie setup" (for beauty products)
- "Car interior" (for casual testimonial vibe)

### Technical Quality Tags

Always end with:
```
photorealistic, 4K, ultra detailed skin texture, natural color grading, shot on Sony A7III
```

Avoid: "8K", "hyperrealistic", "perfect", "stunning" — these push toward AI-uncanny-valley

---

## Example Prompts

### Example 1: General Purpose UGC Girl

```
Beautiful young woman, 23 years old, warm brown eyes, light brown hair with loose beach waves past shoulders. Natural skin texture with light sun-kissed glow, subtle freckles across nose. Mid-conversation expression looking directly at camera, genuine warm smile, slightly raised eyebrows. Wearing a casual white ribbed tank top, small gold hoop earrings, minimal natural makeup. Soft golden hour sunlight from the right side, warm tones. Close-up portrait, head and shoulders, shallow depth of field f/1.8, slightly above eye level selfie angle. Clean bright apartment background with soft bokeh. Photorealistic, 4K, ultra detailed skin texture, natural color grading, shot on Sony A7III
```

### Example 2: Beauty/Skincare UGC Creator

```
Attractive young woman, early 20s, clear dewy skin, dark brown hair in messy bun with loose face-framing pieces. Healthy natural complexion, no visible makeup, fresh-faced morning look. Excited expression, eyes wide with delight, holding hand near chin. Wearing oversized white cotton tee, thin gold chain necklace. Soft ring light illumination, even facial lighting, bright catchlights in both eyes. Tight close-up, face fills most of frame, 35mm equivalent. Clean white bathroom background, slightly blurred. Photorealistic, 4K, ultra detailed skin texture with visible pores, natural dewy finish, shot on iPhone 15 Pro
```

### Example 3: Fitness/Wellness UGC Girl

```
Fit young woman, mid 20s, athletic build, blonde hair pulled back in high ponytail, natural tan. Light sweat on forehead, post-workout glow, healthy flushed cheeks. Bright genuine smile, looking at camera like talking to a friend, relaxed confident posture. Wearing black sports bra, wireless earbuds. Soft outdoor morning light, golden hour warmth on skin. Medium close-up, shoulders and above, shot from slightly below eye level. Gym or outdoor park background with heavy bokeh. Photorealistic, 4K, natural skin texture, athletic physique, candid energy, shot on Sony A7III
```

### Example 4: Luxury/Fashion UGC Creator

```
Elegant young woman, late 20s, sharp jawline, dark hair with curtain bangs, sleek straight style past collarbone. Flawless but natural-looking skin, soft glam makeup with subtle cat eye, nude lip. Confident knowing smile, one eyebrow slightly raised, holding product near face. Wearing beige silk cami top, layered gold necklaces, small diamond studs. Warm directional window light from the left, creating soft shadows. Close-up portrait, head and shoulders, f/1.4 bokeh. Minimalist modern apartment, neutral tones, out of focus. Photorealistic, 4K, ultra detailed skin texture, editorial but approachable, warm color grading
```

### Example 5: Diverse/Inclusive UGC Girl (South Asian)

```
Beautiful South Asian woman, early 20s, warm brown skin with natural glow, long dark wavy hair flowing over one shoulder. Natural skin texture, minimal makeup with bold brows and soft nude lip. Warm inviting smile, looking at camera mid-sentence, one hand gesturing expressively. Wearing casual olive green cropped hoodie, small nose stud, thin gold bangles. Soft golden hour light through window, warm amber tones on skin. Close-up selfie angle, head and shoulders, shallow depth of field. Cozy apartment living room background, fairy lights bokeh. Photorealistic, 4K, ultra detailed skin texture, authentic UGC energy, natural color grading, shot on iPhone 15 Pro
```

---

## Pipeline Usage

This skill is step 1 of the UGC pipeline:

1. **`/ugc-hot-girl`** ← You are here — generates the character image prompt
2. **`/higgsfield-image-auto`** — Takes the prompt to Higgsfield Soul 2.0 and generates the image via Playwright
3. **`/seedance-auto-generate`** — Takes the generated image to the Seedance 2.0 video page, adds a video prompt, and generates a UGC video

### Quick Pipeline Example

```
User: "Create a UGC girl for my skincare brand"

Step 1 → /ugc-hot-girl → generates image prompt (beauty/skincare variant)
Step 2 → /higgsfield-image-auto → automates image generation on Higgsfield Soul 2.0
Step 3 → /seedance-auto-generate → uses the generated image + UGC video prompt to create a Seedance 2.0 video
```
