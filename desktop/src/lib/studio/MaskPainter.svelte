<script lang="ts">
  import { Brush, Eraser, RotateCcw } from '@lucide/svelte';
  import { api } from '../api/client';
  import { mediaUrl } from '../api/transport';
  import { toastError } from '../stores/toast.svelte';
  import Button from '../ui/Button.svelte';
  import Modal from '../ui/Modal.svelte';
  import Segmented from '../ui/Segmented.svelte';
  import Slider from '../ui/Slider.svelte';

  /** Paint a mask over the reference image; white = area to regenerate. */
  let { open = $bindable(), imageId, maskId = $bindable() }: { open: boolean; imageId: string; maskId: string | null } = $props();

  let canvas: HTMLCanvasElement | undefined = $state();
  let img: HTMLImageElement | undefined = $state();
  let tool = $state<'brush' | 'erase'>('brush');
  let size = $state(48);
  let saving = $state(false);
  let drawing = false;
  let last: [number, number] | null = null;

  function setup() {
    if (!canvas || !img) return;
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (maskId) {
      const m = new Image();
      m.crossOrigin = 'anonymous';
      m.onload = () => {
        // Existing masks are white-on-black; show them as violet overlay.
        const tmp = document.createElement('canvas');
        tmp.width = canvas!.width;
        tmp.height = canvas!.height;
        const t = tmp.getContext('2d')!;
        t.drawImage(m, 0, 0, tmp.width, tmp.height);
        const data = t.getImageData(0, 0, tmp.width, tmp.height);
        for (let i = 0; i < data.data.length; i += 4) {
          const v = data.data[i];
          data.data[i] = 167; data.data[i + 1] = 139; data.data[i + 2] = 250; data.data[i + 3] = v > 127 ? 255 : 0;
        }
        ctx.putImageData(data, 0, 0);
      };
      m.src = mediaUrl(`/v1/files/${maskId}`);
    }
  }

  function point(e: PointerEvent): [number, number] {
    const r = canvas!.getBoundingClientRect();
    return [((e.clientX - r.left) / r.width) * canvas!.width, ((e.clientY - r.top) / r.height) * canvas!.height];
  }

  function stroke(p: [number, number]) {
    const ctx = canvas!.getContext('2d')!;
    const scale = canvas!.width / canvas!.getBoundingClientRect().width;
    ctx.globalCompositeOperation = tool === 'brush' ? 'source-over' : 'destination-out';
    ctx.strokeStyle = 'rgb(167,139,250)';
    ctx.fillStyle = 'rgb(167,139,250)';
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = size * scale;
    ctx.beginPath();
    if (last) {
      ctx.moveTo(...last);
      ctx.lineTo(...p);
      ctx.stroke();
    } else {
      ctx.arc(p[0], p[1], (size * scale) / 2, 0, Math.PI * 2);
      ctx.fill();
    }
    last = p;
  }

  async function apply() {
    if (!canvas) return;
    saving = true;
    try {
      const out = document.createElement('canvas');
      out.width = canvas.width;
      out.height = canvas.height;
      const o = out.getContext('2d')!;
      o.fillStyle = 'black';
      o.fillRect(0, 0, out.width, out.height);
      const src = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height);
      const dst = o.getImageData(0, 0, out.width, out.height);
      let any = false;
      for (let i = 0; i < src.data.length; i += 4) {
        if (src.data[i + 3] > 20) {
          dst.data[i] = dst.data[i + 1] = dst.data[i + 2] = 255;
          any = true;
        }
      }
      if (!any) {
        maskId = null;
        open = false;
        return;
      }
      o.putImageData(dst, 0, 0);
      const blob: Blob = await new Promise((res) => out.toBlob((b) => res(b!), 'image/png'));
      const r = await api.upload(blob, 'mask.png');
      maskId = r.id;
      open = false;
    } catch (e) {
      toastError(e, 'Could not save mask');
    } finally {
      saving = false;
    }
  }
</script>

<Modal bind:open title="Inpaint mask" subtitle="Paint over the areas to regenerate." width={860}>
  <div class="tools">
    <Segmented bind:value={tool} items={[{ value: 'brush', label: 'Brush', icon: Brush }, { value: 'erase', label: 'Erase', icon: Eraser }]} />
    <div class="sz"><Slider bind:value={size} min={4} max={200} label="Brush size" unit=" px" /></div>
    <Button size="sm" variant="ghost" onclick={() => { const c = canvas!.getContext('2d')!; c.clearRect(0, 0, canvas!.width, canvas!.height); }}><RotateCcw />Clear</Button>
  </div>
  <div class="paint">
    <img bind:this={img} src={mediaUrl(`/v1/files/${imageId}`)} alt="" crossorigin="anonymous" onload={setup} />
    <canvas bind:this={canvas}
      onpointerdown={(e) => { drawing = true; last = null; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); stroke(point(e)); }}
      onpointermove={(e) => drawing && stroke(point(e))}
      onpointerup={() => { drawing = false; last = null; }}></canvas>
  </div>
  {#snippet footer()}
    <Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
    <Button variant="primary" onclick={apply} loading={saving}>Use mask</Button>
  {/snippet}
</Modal>

<style>
  .tools { display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }
  .sz { width: 220px; }
  .paint { position: relative; display: grid; place-items: center; max-height: 62vh; background: #050507; border-radius: var(--r-md); overflow: hidden; }
  .paint img { max-width: 100%; max-height: 62vh; display: block; user-select: none; -webkit-user-drag: none; }
  canvas { position: absolute; width: 100%; height: 100%; max-width: 100%; opacity: 0.6; cursor: crosshair; touch-action: none; }
  .paint img, canvas { grid-area: 1 / 1; }
  canvas { position: static; }
</style>
