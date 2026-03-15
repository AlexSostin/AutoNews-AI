import React, { forwardRef, useEffect, useImperativeHandle, useState } from 'react'

interface SlashCommandMenuProps {
  items: any[];
  command: (item: any) => void;
}

export const SlashCommandMenu = forwardRef((props: SlashCommandMenuProps, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0)

  const selectItem = (index: number) => {
    const item = props.items[index]
    if (item) {
      props.command(item)
    }
  }

  const upHandler = () => {
    setSelectedIndex((selectedIndex + props.items.length - 1) % props.items.length)
  }

  const downHandler = () => {
    setSelectedIndex((selectedIndex + 1) % props.items.length)
  }

  const enterHandler = () => {
    selectItem(selectedIndex)
  }

  useEffect(() => {
    setSelectedIndex(0)
  }, [props.items])

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: { event: KeyboardEvent }) => {
      if (event.key === 'ArrowUp') {
        upHandler()
        return true
      }
      if (event.key === 'ArrowDown') {
        downHandler()
        return true
      }
      if (event.key === 'Enter') {
        enterHandler()
        return true
      }
      return false
    },
  }))

  if (!props.items.length) {
    return null
  }

  return (
    <div className="bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden w-64 text-sm z-50 animate-in fade-in slide-in-from-top-2 duration-100">
      <div className="px-3 py-2 text-xs font-semibold tracking-wider text-gray-500 bg-gray-50/80 border-b border-gray-100 uppercase">
        Create Blocks & Actions
      </div>
      <div className="p-1 max-h-[300px] overflow-y-auto">
        {props.items.map((item: any, index: number) => (
          <button
            key={index}
            className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              index === selectedIndex ? 'bg-indigo-50 text-indigo-900' : 'text-gray-700 hover:bg-gray-50'
            }`}
            onClick={() => selectItem(index)}
          >
            <div className={`w-8 h-8 rounded-md flex items-center justify-center border font-medium ${
              index === selectedIndex ? 'bg-white border-indigo-200 text-indigo-600 shadow-sm' : 'bg-gray-50 border-gray-200 text-gray-500'
            }`}>
              {item.icon}
            </div>
            <div>
              <div className={`font-medium ${index === selectedIndex ? 'text-indigo-900' : 'text-gray-900'}`}>
                {item.title}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">{item.description}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
})

SlashCommandMenu.displayName = 'SlashCommandMenu'
