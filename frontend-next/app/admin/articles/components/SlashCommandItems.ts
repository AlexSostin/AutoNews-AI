import { ReactRenderer } from '@tiptap/react'
import type { Editor, Range } from '@tiptap/core'
import tippy, { GetReferenceClientRect, Instance } from 'tippy.js'
import { SlashCommandMenu } from './SlashCommandMenu'

export const getSuggestionItems = ({ query }: { query: string }) => {
  return [
    {
      title: 'AI Copilot',
      description: 'Ask AI to write or edit',
      icon: '✨',
      command: ({ editor, range }: { editor: Editor, range: Range }) => {
        editor.chain().focus().deleteRange(range).run()
        // Trigger a custom event that page.tsx can listen to
        window.dispatchEvent(new CustomEvent('open-ai-copilot'))
      },
    },
    {
      title: 'Heading 2',
      description: 'Big section heading',
      icon: 'H2',
      command: ({ editor, range }: { editor: Editor, range: Range }) => {
        editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run()
      },
    },
    {
      title: 'Heading 3',
      description: 'Small section heading',
      icon: 'H3',
      command: ({ editor, range }: { editor: Editor, range: Range }) => {
        editor.chain().focus().deleteRange(range).setNode('heading', { level: 3 }).run()
      },
    },
    {
      title: 'Bullet List',
      description: 'Create a simple bulleted list',
      icon: '•',
      command: ({ editor, range }: { editor: Editor, range: Range }) => {
        editor.chain().focus().deleteRange(range).toggleBulletList().run()
      },
    },
    {
      title: 'Numbered List',
      description: 'Create a list with numbering',
      icon: '1.',
      command: ({ editor, range }: { editor: Editor, range: Range }) => {
        editor.chain().focus().deleteRange(range).toggleOrderedList().run()
      },
    },
    {
      title: 'Quote',
      description: 'Capture a quote',
      icon: '""',
      command: ({ editor, range }: { editor: Editor, range: Range }) => {
        editor.chain().focus().deleteRange(range).toggleBlockquote().run()
      },
    },
  ].filter(item => item.title.toLowerCase().startsWith(query.toLowerCase()))
}

export const renderItems = () => {
  let component: ReactRenderer
  let popup: Instance[]

  return {
    onStart: (props: Record<string, unknown> & { editor: Editor, clientRect?: GetReferenceClientRect }) => {
      component = new ReactRenderer(SlashCommandMenu, {
        props,
        editor: props.editor,
      })

      if (!props.clientRect) {
        return
      }

      popup = tippy('body', {
        getReferenceClientRect: props.clientRect,
        appendTo: () => document.body,
        content: component.element,
        showOnCreate: true,
        interactive: true,
        trigger: 'manual',
        placement: 'bottom-start',
      })
    },

    onUpdate(props: Record<string, unknown> & { clientRect?: GetReferenceClientRect }) {
      component.updateProps(props)

      if (!props.clientRect) {
        return
      }

      popup[0].setProps({
        getReferenceClientRect: props.clientRect,
      })
    },

    onKeyDown(props: { event: KeyboardEvent }) {
      if (props.event.key === 'Escape') {
        popup[0].hide()
        return true
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (component.ref as any)?.onKeyDown(props)
    },

    onExit() {
      popup[0].destroy()
      component.destroy()
    },
  }
}
