# Page snapshot

```yaml
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
  - generic [ref=e27]:
    - paragraph [ref=e28]:
      - text: Don't have an account?
      - link "Register here" [ref=e29] [cursor=pointer]:
        - /url: /register
    - link "← Back to Home" [ref=e30] [cursor=pointer]:
      - /url: /
```