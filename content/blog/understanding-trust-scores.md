---
title: "Understanding HuggingHugh Trust Scores"
slug: understanding-trust-scores
date: 2025-12-26
category: Guide
excerpt: "A deep dive into how we calculate trust scores for AI models and what each factor means for your security."
read_time: 7
---

Every model on HuggingHugh gets a trust score from 0 to 100. But what goes into that number? This guide explains our methodology and helps you interpret scores for your specific use case.

## The Trust Score Philosophy

We designed our scoring system around one principle: **security should be the default, not an afterthought**.

Traditional model leaderboards rank by performance metrics like accuracy or perplexity. HuggingHugh ranks by security posture. A model that scores 95% on benchmarks but uses unsafe serialization formats isn't necessarily a good choice for production.

## The Eight Trust Factors

Our trust score combines eight weighted factors:

### 1. Publisher Reputation (12 points)

Who created this model matters. We maintain a list of verified organizations with strong security track records:

- **12 points**: Verified organizations (OpenAI, Google, Meta, Microsoft, etc.)
- **8 points**: Known community contributors with history
- **4 points**: Unknown publishers with high download counts
- **0 points**: New or anonymous publishers

### 2. SafeTensors Format (18 points)

Does the model use SafeTensors, the secure serialization format?

- **18 points**: SafeTensors only, no pickle files
- **12 points**: SafeTensors available, but pickle also present
- **0 points**: Pickle only, no SafeTensors

### 3. No Pickle Files (18 points)

A stricter check for dangerous file types:

- **18 points**: No `.bin`, `.pkl`, or `.pickle` files
- **9 points**: Pickle files present but SafeTensors available
- **0 points**: Pickle files with no safe alternative

### 4. Vulnerability Count (15 points)

We scan inferred dependencies for known CVEs:

- **15 points**: No known vulnerabilities
- **12 points**: Low severity only
- **8 points**: Medium severity
- **4 points**: High severity
- **0 points**: Critical vulnerabilities

### 5. License Clarity (10 points)

Is the license clear and appropriate?

- **10 points**: Permissive open source (MIT, Apache 2.0)
- **8 points**: Commercial-friendly with restrictions
- **5 points**: Copyleft (GPL, AGPL)
- **2 points**: Restrictive or unclear
- **0 points**: No license specified

### 6. Recent Updates (8 points)

Is the model actively maintained?

- **8 points**: Updated within 30 days
- **6 points**: Updated within 90 days
- **4 points**: Updated within 180 days
- **2 points**: Updated within 365 days
- **0 points**: No updates in over a year

### 7. Community Engagement (7 points)

A proxy for community trust and oversight:

- **7 points**: High engagement (1000+ likes)
- **5 points**: Medium engagement (100-999 likes)
- **3 points**: Low engagement (10-99 likes)
- **1 point**: Minimal engagement

### 8. Documentation Quality (12 points)

Does the model have proper documentation?

- **12 points**: Complete model card with usage examples
- **8 points**: Basic model card
- **4 points**: Minimal README
- **0 points**: No documentation

## Grade Boundaries

Scores map to letter grades:

| Grade | Score Range | Interpretation |
|-------|-------------|----------------|
| A | 90-100 | Excellent security posture |
| B | 80-89 | Good, minor concerns |
| C | 70-79 | Moderate, review before production |
| D | 60-69 | Low, significant concerns |
| F | 0-59 | Poor, high risk |

## What the Scores Mean in Practice

### Score 90+ (Grade A)

These models follow security best practices. They use SafeTensors, come from verified publishers, have clear licenses, and are actively maintained. You can deploy these with confidence after standard review.

### Score 80-89 (Grade B)

Good models with minor gaps. Maybe they have pickle files alongside SafeTensors, or the license has some restrictions. Worth investigating the specific concerns before production use.

### Score 70-79 (Grade C)

Moderate risk. These models might come from unknown publishers, lack recent updates, or have dependency vulnerabilities. Use in development is fine, but production deployments need extra scrutiny.

### Score 60-69 (Grade D)

Significant concerns. Often means pickle-only format from unknown publishers with potential vulnerabilities. Consider finding an alternative or forking to fix issues.

### Score Below 60 (Grade F)

High risk. Multiple red flags across security factors. These models might still work, but they represent substantial supply chain risk. Only use if you can audit and remediate the issues yourself.

## Limitations

Our scoring has known limitations:

1. **Inference, not certainty**: We infer dependencies from model metadata; we don't execute the model
2. **Static analysis**: We can't detect runtime behaviors or model-level attacks
3. **Publisher reputation lag**: New organizations take time to build trust scores
4. **Point-in-time**: Scores reflect current state; models can improve or degrade

## Using Scores Effectively

1. **Set minimum thresholds** for your organization (e.g., "no models below 70")
2. **Review the breakdown** not just the total score
3. **Prioritize security factors** relevant to your use case
4. **Re-check periodically** as models and dependencies update
5. **Combine with other tools** like your own security scanning

## Conclusion

Trust scores are a starting point, not a final verdict. They highlight potential risks so you can make informed decisions. A low score doesn't mean a model is malicious; it means you should investigate before deploying.

Browse our dashboard to see how your favorite models score, and use the individual report pages to understand specific risk factors.
