ci:
  collect:
    url:
      - http://localhost:3000/
      - http://localhost:3000/articles
      - http://localhost:3000/login
    startServerCommand: pnpm dev
    startServerReadyPattern: 'ready started server'
    startServerReadyTimeout: 30000
  upload:
    target: temporary-public-storage
  assert:
    preset: lighthouse:recommended
    assertions:
      # Performance
      first-contentful-paint: ['warn', { maxNumericValue: 3000 }]
      largest-contentful-paint: ['warn', { maxNumericValue: 4000 }]
      cumulative-layout-shift: ['warn', { maxNumericValue: 0.1 }]
      total-blocking-time: ['warn', { maxNumericValue: 500 }]
      
      # Accessibility
      categories:accessibility: ['error', { minScore: 0.9 }]
      
      # Best Practices
      categories:best-practices: ['warn', { minScore: 0.8 }]
      
      # SEO
      categories:seo: ['warn', { minScore: 0.9 }]
      
      # Specific checks (relaxed for development)
      uses-responsive-images: 'off'
      offscreen-images: 'off'
      unused-javascript: 'off'
