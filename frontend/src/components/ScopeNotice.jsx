import { useAuth } from "../auth/useAuth";

/** Shown to people who can only see some classes, so a short list never looks like missing data. */
function ScopeNotice() {
  const { user } = useAuth();
  if (user.role === "admin" || user.scope !== "classes") return null;
  const classes = user.classes.length > 0 ? user.classes.join(", ") : "none yet";
  return (
    <p className="notice notice--info" role="note">
      You can see students in these classes: {classes}. Ask an administrator if a class is missing.
    </p>
  );
}

export default ScopeNotice;
