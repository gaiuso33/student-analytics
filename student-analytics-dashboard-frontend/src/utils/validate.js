// Keep these limits in sync with the backend (validation.py / config.py).
export const MIN_PASSWORD_LENGTH = 10;

export function validateName(name, label = "Name") {
  const value = name.trim();
  if (!value) return `${label} is required`;
  if (value.length > 100) return `${label} must be at most 100 characters`;
  return null;
}

/** Takes the raw form strings; returns { field: message } (empty object when valid). */
export function validateResult({ course, semester, score }) {
  const errors = {};
  if (!course.trim()) errors.course = "Course is required";
  else if (course.trim().length > 60) errors.course = "Course must be at most 60 characters";

  if (!semester.trim()) errors.semester = "Semester is required";
  else if (semester.trim().length > 20) errors.semester = "Semester must be at most 20 characters";

  const n = score.trim() === "" ? NaN : Number(score);
  if (Number.isNaN(n) || n < 0 || n > 100) errors.score = "Score must be a number from 0 to 100";
  return errors;
}

export function validatePassword(password) {
  if (password.length < MIN_PASSWORD_LENGTH) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters`;
  if (password.length > 128) return "Password must be at most 128 characters";
  return null;
}

export function validateUsername(username) {
  return /^[A-Za-z0-9_.-]{3,32}$/.test(username.trim())
    ? null
    : "Username must be 3-32 characters: letters, numbers, dot, dash or underscore";
}
