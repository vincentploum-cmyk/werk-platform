import { useEffect, useRef, useState } from 'react'

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
  'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Dialog behavior for modals and side sheets: initial focus, focus trap,
 * Escape to close, and focus restore to the opener on unmount.
 *
 * Attach the returned ref to the dialog container and give it
 * role="dialog" aria-modal="true" and an aria-label.
 */
export function useDialog<T extends HTMLElement>(onClose: () => void) {
  const ref = useRef<T>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  // Captured during render — effects run AFTER React applies a child's autoFocus,
  // by which point activeElement would already be inside the dialog.
  const [opener] = useState(() => document.activeElement as HTMLElement | null)

  useEffect(() => {
    const node = ref.current

    // Initial focus: prefer an element marked [data-autofocus] (a real DOM
    // attribute, so it survives React StrictMode's dev remount unlike the
    // autoFocus prop), else the first focusable element, else the dialog.
    if (node) {
      const target =
        node.querySelector<HTMLElement>('[data-autofocus]') ??
        node.querySelector<HTMLElement>(FOCUSABLE) ??
        node
      if (target !== document.activeElement) target.focus()
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onCloseRef.current()
        return
      }
      if (e.key !== 'Tab' || !ref.current) return
      const els = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.getClientRects().length > 0,
      )
      if (els.length === 0) return
      const first = els[0]
      const last = els[els.length - 1]
      const active = document.activeElement
      if (e.shiftKey && (active === first || !ref.current.contains(active))) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (active === last || !ref.current.contains(active))) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      opener?.focus()
    }
  }, [opener])

  return ref
}
