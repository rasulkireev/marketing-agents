module.exports = {
  content: [
    './frontend/templates/**/*.html',
    './frontend/src/**/*.js',
    './core/**/*.py',
  ],
  theme: {
    extend: {
      keyframes: {
        enter: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        }
      },
      animation: {
        enter: 'enter 0.3s ease-out'
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
};
