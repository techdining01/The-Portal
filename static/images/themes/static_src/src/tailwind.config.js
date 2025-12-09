// theme/static_src/tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  // CRITICAL: This ensures Tailwind scans ALL your HTML, Python, and JS files
  // for classes (e.g., 'bg-blue-600', 'flex', etc.)
  content: [
    '../templates/**/*.html',
    '../../**/templates/**/*.html',
    '../../**/*.py',
    '../../**/*.js',
  ],
  theme: {
    extend: {
      // You can define custom theme extensions here later
    },
  },
  // Add common plugins
  plugins: [],
}