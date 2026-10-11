export const ROLE_LABELS = { admin: "Administrator", staff: "Staff", viewer: "Viewer" };

export const roleLabel = (role) => ROLE_LABELS[role] ?? role;
