interface IconProps {
  size?: number;
  className?: string;
}

export function WorkspacesIcon({ size = 20, className = '' }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Grid of three "workspace" cells — top-left, top-right, bottom spanning */}
      <rect x="2" y="2" width="7" height="7" rx="1.5"
        fill="currentColor" opacity="0.85" />
      <rect x="11" y="2" width="7" height="7" rx="1.5"
        fill="currentColor" opacity="0.5" />
      <rect x="2" y="11" width="16" height="7" rx="1.5"
        fill="currentColor" opacity="0.3" />
      {/* Active indicator dot on top-left cell */}
      <circle cx="5.5" cy="5.5" r="1.25" fill="white" opacity="0.9" />
    </svg>
  );
}

export function StructuralHazardsIcon({ size = 20, className = '' }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Warning triangle */}
      <path
        d="M10 2.5L17.5 16H2.5L10 2.5Z"
        fill="currentColor"
        opacity="0.2"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Exclamation stem */}
      <line
        x1="10" y1="8.5"
        x2="10" y2="12.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      {/* Exclamation dot */}
      <circle cx="10" cy="14.5" r="0.9" fill="currentColor" />
    </svg>
  );
}

export function EngineActiveIcon({ size = 20, className = '' }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer pulse ring */}
      <circle cx="10" cy="10" r="8"
        stroke="currentColor" strokeWidth="1" opacity="0.2" />
      {/* Mid ring */}
      <circle cx="10" cy="10" r="5.5"
        stroke="currentColor" strokeWidth="1.25" opacity="0.45" />
      {/* Core filled circle */}
      <circle cx="10" cy="10" r="3" fill="currentColor" />
      {/* Activity tick marks — north, east, south, west */}
      <line x1="10" y1="1.5" x2="10" y2="3"   stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="18.5" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="10" y1="18.5" x2="10" y2="17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="1.5" y1="10" x2="3" y2="10"   stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
