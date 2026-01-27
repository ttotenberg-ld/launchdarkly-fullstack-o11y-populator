# Traffic Simulator Architecture

This document describes the architecture and flow of the LaunchDarkly Observability Demo traffic simulator.

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Simulator["Traffic Generator"]
        TG[TrafficGenerator]
        CSS[ComprehensiveSessionScenario]
        HT[HumanTypist]
        HC[HumanClicker]
    end

    subgraph Browser["Playwright Browser"]
        BC[BrowserContext]
        P[Page]
    end

    subgraph Frontend["React Frontend"]
        Home[Home Page]
        Products[Products Page]
        ProductDetail[Product Detail]
        Search[Search]
        Login[Login Page]
        Account[Account Page]
        Cart[Cart Page]
        Checkout[Checkout Page]
    end

    subgraph Backend["Backend Services"]
        API[API Gateway]
        Auth[Auth Service]
        User[User Service]
        Prod[Product Service]
        Inv[Inventory Service]
        Order[Order Service]
        Pay[Payment Service]
        SearchSvc[Search Service]
        Notif[Notification Service]
    end

    TG --> BC
    BC --> P
    P --> Frontend
    Frontend --> API
    API --> Auth
    API --> User
    API --> Prod
    API --> Inv
    API --> Order
    API --> Pay
    API --> SearchSvc
    API --> Notif
```

## Session Flow

Each simulated session follows this comprehensive flow to hit all backend endpoints:

```mermaid
flowchart TD
    Start([Session Start]) --> SelectUser[Select Random User Persona]
    SelectUser --> Phase1

    subgraph Phase1["Phase 1: Landing"]
        P1A[Navigate to Home] --> P1B[Read Page 2-4s]
        P1B --> P1C[Scroll Randomly]
        P1C --> P1D[Hover Navigation Elements]
    end

    Phase1 --> Phase2

    subgraph Phase2["Phase 2: Browse Products"]
        P2A[Navigate to /products] --> P2B[Read Page 2-4s]
        P2B --> P2C[Scroll & Hover Product Cards]
        P2C --> P2D[Click 1-2 Products]
        P2D --> P2E[View Product Details]
        P2E --> P2F[Go Back to List]
    end

    Phase2 --> Phase3

    subgraph Phase3["Phase 3: Search"]
        P3A[Find Search Input] --> P3B{Make Typos?}
        P3B -->|Yes 70%| P3C[Type with Typos]
        P3B -->|No 30%| P3D[Type Correctly]
        P3C --> P3E[Notice Mistake]
        P3E --> P3F[Clear & Retype]
        P3F --> P3G[Submit Search]
        P3D --> P3G
        P3G --> P3H[View Results]
    end

    Phase3 --> Phase4

    subgraph Phase4["Phase 4: Login"]
        P4A[Navigate to /login] --> P4B{Demo Login Available?}
        P4B -->|Yes| P4C[Click Demo Login Button]
        P4B -->|No| P4D[Type Email Slowly]
        P4D --> P4E[Type Password Fast]
        P4E --> P4F[Click Login]
        P4C --> P4G[Wait for Auth]
        P4F --> P4G
    end

    Phase4 --> Phase5

    subgraph Phase5["Phase 5: Account"]
        P5A[View /account] --> P5B[Read User Data]
        P5B --> P5C[View Dashboard]
        P5C --> P5D[View Orders]
    end

    Phase5 --> Phase6

    subgraph Phase6["Phase 6: Checkout"]
        P6A[Browse Products] --> P6B[Select Product]
        P6B --> P6C[Add to Cart]
        P6C --> P6D[View Cart]
        P6D --> P6E[Start Checkout]
        P6E --> P6F[Fill Shipping Form]
        P6F --> P6G[Fill Payment Form]
        P6G --> P6H[Place Order]
        P6H --> P6I[Order Confirmation]
    end

    Phase6 --> Phase7

    subgraph Phase7["Phase 7: Final Exploration"]
        P7A{Time Remaining?}
        P7A -->|Yes| P7B[Random Action]
        P7B --> P7C[Browse/Scroll/Navigate]
        P7C --> P7A
        P7A -->|No| End
    end

    End([Session End])
```

## Human-Like Behaviors

The simulator implements realistic human behaviors:

```mermaid
flowchart LR
    subgraph HumanTypist["Human Typist Behaviors"]
        T1[Variable WPM 30-60]
        T2[Random Delays Between Keys]
        T3[Longer Pauses at Spaces]
        T4[10% Typo Chance]
        T5[Backspace Corrections]
    end

    subgraph HumanClicker["Human Clicker Behaviors"]
        C1[Hesitate Before Click]
        C2[Random Scrolling]
        C3[Hover Over Elements]
        C4[Variable Scroll Amounts]
    end

    subgraph Timing["Timing Delays"]
        D1["hesitate() 0.5-2s"]
        D2["read_page() 2-5s"]
        D3["quick_glance() 0.5-1.5s"]
    end
```

## API Endpoints Coverage

Each session is designed to hit all major backend endpoints:

```mermaid
flowchart TB
    subgraph Endpoints["Backend Endpoints Hit Per Session"]
        E1["/api/health"]
        E2["/api/dashboard"]
        E3["/api/login"]
        E4["/api/users/:id"]
        E5["/api/products"]
        E6["/api/products/:id"]
        E7["/api/search"]
        E8["/api/checkout"]
        E9["/api/orders"]
    end

    subgraph Phases["Session Phases"]
        Landing --> E1
        Browse --> E5
        Browse --> E6
        Search --> E7
        Login --> E3
        Account --> E4
        Account --> E2
        Checkout --> E8
        Checkout --> E9
    end
```

## Configuration

```mermaid
flowchart LR
    subgraph Config["Environment Variables"]
        C1["FRONTEND_URL<br/>default: localhost:3000"]
        C2["SESSIONS_PER_MINUTE<br/>default: 2"]
        C3["MAX_CONCURRENT_BROWSERS<br/>default: 3"]
        C4["TARGET_SESSION_DURATION<br/>default: 30s"]
    end

    subgraph Stats["Runtime Statistics"]
        S1[Session Count]
        S2[Success Count]
        S3[Error Count]
        S4[Error Rate %]
    end

    Config --> Generator[TrafficGenerator]
    Generator --> Stats
```

## Class Diagram

```mermaid
classDiagram
    class TrafficGenerator {
        -sessions_per_minute: int
        -session_count: int
        -error_count: int
        -success_count: int
        -browser: Browser
        -semaphore: Semaphore
        -scenario: ComprehensiveSessionScenario
        +select_user() dict
        +run_session(context) Dict
        +run_forever()
        +run()
    }

    class ComprehensiveSessionScenario {
        -name: str
        -target_duration: int
        -endpoints_hit: set
        +execute(page, user) Dict
        -_phase_landing(page, results)
        -_phase_browse_products(page, results)
        -_phase_search(page, results)
        -_phase_login(page, user, results)
        -_phase_account(page, user, results)
        -_phase_checkout(page, user, results)
        -_fill_shipping_form(page, user, results)
        -_fill_payment_form(page, user, results)
        -_phase_final_exploration(page, results, time)
    }

    class HumanTypist {
        +type_like_human(page, selector, text, typos, wpm)$
        +hesitate(min, max)$
        +read_page(min, max)$
        +quick_glance(min, max)$
    }

    class HumanClicker {
        +click_with_hesitation(page, selector, before, after)$
        +scroll_randomly(page, times)$
        +explore_hover(page, selector)$
    }

    TrafficGenerator --> ComprehensiveSessionScenario
    ComprehensiveSessionScenario --> HumanTypist
    ComprehensiveSessionScenario --> HumanClicker
```

## Sequence Diagram - Single Session

```mermaid
sequenceDiagram
    participant TG as TrafficGenerator
    participant CSS as SessionScenario
    participant HT as HumanTypist
    participant HC as HumanClicker
    participant Page as Browser Page
    participant FE as Frontend
    participant BE as Backend API

    TG->>TG: select_user()
    TG->>Page: new_page()
    TG->>CSS: execute(page, user)
    
    Note over CSS: Phase 1: Landing
    CSS->>Page: goto(home)
    Page->>FE: Load Home
    FE->>BE: GET /api/health
    CSS->>HT: read_page(2-4s)
    CSS->>HC: scroll_randomly()
    
    Note over CSS: Phase 2: Browse
    CSS->>Page: goto(products)
    Page->>FE: Load Products
    FE->>BE: GET /api/products
    CSS->>HC: explore_hover(product-cards)
    CSS->>Page: click(product)
    FE->>BE: GET /api/products/:id
    
    Note over CSS: Phase 3: Search
    CSS->>HT: type_like_human(query)
    HT-->>Page: type with delays/typos
    CSS->>Page: submit search
    FE->>BE: GET /api/search
    
    Note over CSS: Phase 4: Login
    CSS->>Page: goto(login)
    CSS->>HT: type_like_human(email)
    CSS->>HT: type_like_human(password)
    CSS->>Page: click(login)
    FE->>BE: POST /api/login
    
    Note over CSS: Phase 5: Account
    CSS->>Page: goto(account)
    FE->>BE: GET /api/users/:id
    FE->>BE: GET /api/dashboard
    
    Note over CSS: Phase 6: Checkout
    CSS->>Page: add_to_cart()
    CSS->>Page: goto(checkout)
    CSS->>HT: fill shipping form
    CSS->>HT: fill payment form
    CSS->>Page: place_order()
    FE->>BE: POST /api/checkout
    FE->>BE: GET /api/orders
    
    CSS-->>TG: return results
    TG->>Page: close()
```
