const ICONS = {
  dashboard: <><rect x="2" y="2" width="5" height="5" rx="1" />
    <rect x="9" y="2" width="5" height="5" rx="1" /><rect x="2" y="9" width="5" height="5" rx="1" />
    <rect x="9" y="9" width="5" height="5" rx="1" /></>,
  attention: <>
    <path d="M8 2.3 14 13H2Z" />
    <path d="M8 6v3.2m0 1.9v.1" />
  </>,
  usage: <>
    <rect x="2" y="2.5" width="12" height="11" rx="2" />
    <path d="M5 10V8m3 2V5m3 5V7" />
  </>,
  setup: <>
    <rect x="2.5" y="2" width="11" height="12" rx="2" />
    <path d="m4.6 5.4.8.8L6.9 4.7M9 5.5h2m-6.4 5 .8.8 1.5-1.5M9 10.5h2" />
  </>,
  settings: <>
    <path d="M6.5 1.8h3l.4 1.6 1.3.8 1.6-.5 1.5 2.6-1.2 1.1v1.5l1.2 1.1-1.5 2.6-1.6-.5-1.3.8-.4 1.6h-3
      l-.4-1.6-1.3-.8-1.6.5-1.5-2.6 1.2-1.1V7.4L1.7 6.3l1.5-2.6 1.6.5 1.3-.8Z" />
    <circle cx="8" cy="8" r="2.3" />
  </>,
  theme: <>
    <circle cx="8" cy="8" r="6" />
    <path d="M8 2a6 6 0 0 0 0 12V2Z" />
  </>,
  synthetic: <>
    <path d="M6 2h4M7 2v4l-4 6.2A1.2 1.2 0 0 0 4 14h8a1.2 1.2 0 0 0 1-1.8L9 6V2M5 10h6" />
  </>,
  collapse: <path d="m9.5 4-4 4 4 4" />,
  expand: <path d="m6.5 4 4 4-4 4" />,
};

export function ShellIcon({ name, class: className = '', ...props }) {
  return <svg {...props} class={`shell-icon${className ? ` ${className}` : ''}`}
    width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"
    fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
    {ICONS[name]}
  </svg>;
}
