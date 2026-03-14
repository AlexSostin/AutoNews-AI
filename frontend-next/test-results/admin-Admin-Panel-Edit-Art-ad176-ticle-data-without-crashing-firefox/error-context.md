# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e4]:
    - link "Fresh Motors" [ref=e6] [cursor=pointer]:
      - /url: /
      - img "Fresh Motors" [ref=e7]
    - generic [ref=e8]:
      - generic [ref=e9]:
        - generic [ref=e10]: Username
        - textbox "Username" [ref=e11]
      - generic [ref=e12]:
        - generic [ref=e13]: Password
        - textbox "Password" [ref=e14]
        - button "Show password" [ref=e15]:
          - img [ref=e16]
      - button "Login" [ref=e19]
    - generic [ref=e24]: Or continue with
    - generic [ref=e28]:
      - button "להמשיך עם Google. פתיחה בכרטיסייה חדשה" [ref=e30] [cursor=pointer]:
        - generic [ref=e32]:
          - img [ref=e34]
          - generic [ref=e40]: להמשיך עם Google
      - generic:
        - iframe
        - button "כניסה באמצעות חשבון Google. פתיחה בכרטיסייה חדשה"
    - generic [ref=e41]:
      - paragraph [ref=e42]:
        - text: Don't have an account?
        - link "Register here" [ref=e43] [cursor=pointer]:
          - /url: /register
      - link "← Back to Home" [ref=e44] [cursor=pointer]:
        - /url: /
  - alert [ref=e45]
```