<script lang="ts">
  import Button from './Button.svelte';
  import Modal from './Modal.svelte';
  import TextInput from './TextInput.svelte';
  import { dialog } from './dialogs.svelte';

  let value = $state('');
  let open = $state(false);
  $effect(() => {
    if (dialog.current) {
      value = dialog.current.value ?? '';
      open = true;
    }
  });
  function finish(ok: boolean) {
    const d = dialog.current;
    if (!d) return;
    open = false;
    dialog.current = null;
    d.resolve(d.kind === 'confirm' ? ok : ok ? value.trim() || null : null);
  }
</script>

{#if dialog.current}
  {@const d = dialog.current}
  <Modal bind:open title={d.title} width={440} onclose={() => finish(false)}>
    {#if d.body}<p class="muted body">{d.body}</p>{/if}
    {#if d.kind === 'prompt'}
      <form onsubmit={(e) => { e.preventDefault(); finish(true); }}>
        <!-- svelte-ignore a11y_autofocus -->
        <TextInput bind:value placeholder={d.placeholder ?? ''} autofocus />
      </form>
    {/if}
    {#snippet footer()}
      <Button variant="ghost" onclick={() => finish(false)}>Cancel</Button>
      <Button variant={d.danger ? 'danger' : 'primary'} onclick={() => finish(true)}>{d.confirmLabel ?? (d.kind === 'prompt' ? 'Save' : 'Confirm')}</Button>
    {/snippet}
  </Modal>
{/if}

<style>
  .body { margin-bottom: 12px; line-height: 1.55; white-space: pre-wrap; }
</style>
