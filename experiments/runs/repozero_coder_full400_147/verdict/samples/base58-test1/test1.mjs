#!/usr/bin/env node

// Base58 encoding implementation in pure JavaScript (ES Modules)
// Based on the reference Python implementation using base58 library

const ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

// Helper function to convert bytes to Base58 string
function bytesToBase58(bytes) {
  if (bytes.length === 0) return '';
  
  // Convert bytes to big-endian number representation
  let num = BigInt(0);
  for (let i = 0; i < bytes.length; i++) {
    num = num * 256n + BigInt(bytes[i]);
  }
  
  // Encode to Base58
  let result = '';
  while (num > 0n) {
    const remainder = num % 58n;
    result = ALPHABET[Number(remainder)] + result;
    num = num / 58n;
  }
  
  // Add leading zeros (based on leading zero bytes in input)
  for (let i = 0; i < bytes.length && bytes[i] === 0; i++) {
    result = '1' + result;
  }
  
  return result;
}

// Parse command line arguments
function parseArgs() {
  const args = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i].replace(/^--/, '');
    const value = process.argv[i + 1];
    args[key] = value;
  }
  return args;
}

// Main execution
const args = parseArgs();

// Handle the case where --a is not provided (should behave like Python)
const inputString = args.a || '';
const encodedBytes = new TextEncoder().encode(inputString);
const result = bytesToBase58(encodedBytes);

console.log(`b'${result}'`);