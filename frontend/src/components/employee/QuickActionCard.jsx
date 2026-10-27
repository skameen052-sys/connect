import React from 'react';

export default function QuickActionCard({
  title,
  icon: Icon,
  iconBg,
  iconColor,
  onClick,
  badgeCount = 0,
}) {
  const count = typeof badgeCount === 'number' ? badgeCount : parseInt(badgeCount, 10) || 0;
  const displayCount = count > 99 ? '99+' : count;

  return (
    <button
      type="button"
      className="quick-action-card"
      onClick={onClick}
    >
      <div
        className="action-card-icon"
        style={{ backgroundColor: iconBg, color: iconColor }}
      >
        <Icon size={22} strokeWidth={2.2} />
        {count > 0 && (
          <span
            className="action-card-badge"
            aria-label={`${displayCount} unread ${title} notifications`}
          >
            {displayCount}
          </span>
        )}
      </div>
      <span className="action-card-title">{title}</span>
    </button>
  );
}

