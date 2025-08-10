# Use official Node.js LTS image
FROM node:alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

# Copy rest of the source code
COPY . .

# Build Next.js app
RUN yarn build

# Production image
FROM node:alpine AS runner
WORKDIR /app

# Copy built files and node_modules from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Expose Next.js default port
EXPOSE 3000

# Run the production server
CMD ["yarn", "start"]
