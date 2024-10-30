module.exports = {
  content: [
    './frontend/templates/**/*.html',
    './core/**/*.py',
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
};
