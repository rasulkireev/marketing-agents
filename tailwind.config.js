module.exports = {
  content: [
    './frontend/templates/**/*.html',
    './frontend/src/**/*.js',
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
