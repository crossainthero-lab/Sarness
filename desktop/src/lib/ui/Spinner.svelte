<script lang="ts">
  let { size = 16 }: { size?: number } = $props();
</script>

<span class="spinner" style="width:{size}px;height:{size}px" aria-hidden="true"></span>

<style>
  .spinner {
    display: inline-block;
    border-radius: 50%;
    border: 2px solid rgba(var(--fg-rgb), 0.14);
    border-top-color: var(--lavender);
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }
</style>
