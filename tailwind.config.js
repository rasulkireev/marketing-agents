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
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      animation: {
        enter: 'enter 0.3s ease-out',
        'fade-in': 'fadeIn 0.5s ease-in',
        'fade-in-delay': 'fadeIn 0.5s ease-in 0.2s',
        'slide-up': 'slideUp 0.5s ease-out',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
};
