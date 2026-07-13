// Base58 implementation for test10
const BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

// Base58 encode function
function b58encode(input) {
  if (input.length === 0) return '';
  
  // Convert input to big-endian bytes
  let bytes = [];
  for (let i = 0; i < input.length; i++) {
    bytes.push(input[i]);
  }
  
  // Convert bytes to big integer (base 256)
  let value = BigInt(0);
  for (let i = 0; i < bytes.length; i++) {
    value = value * 256n + BigInt(bytes[i]);
  }
  
  // Convert big integer to base 58
  if (value === 0n) return '1';
  
  let result = '';
  while (value > 0n) {
    const remainder = value % 58n;
    result = BASE58_ALPHABET[Number(remainder)] + result;
    value = value / 58n;
  }
  
  // Add leading zeros (based on original input)
  let leadingZeros = 0;
  for (let i = 0; i < input.length && input[i] === 0; i++) {
    leadingZeros++;
  }
  
  return '1'.repeat(leadingZeros) + result;
}

// Base58 decode function
function b58decode(input) {
  if (input.length === 0) return new Uint8Array(0);
  
  // Count leading zeros
  let leadingZeros = 0;
  for (let i = 0; i < input.length && input[i] === '1'; i++) {
    leadingZeros++;
  }
  
  // Convert base58 to big integer
  let value = 0n;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    const index = BASE58_ALPHABET.indexOf(char);
    if (index === -1) {
      throw new Error('Invalid base58 character');
    }
    value = value * 58n + BigInt(index);
  }
  
  // Convert big integer to bytes
  const bytes = [];
  while (value > 0n) {
    bytes.unshift(Number(value % 256n));
    value = value / 256n;
  }
  
  // Pad with leading zeros if needed
  while (bytes.length < leadingZeros) {
    bytes.unshift(0);
  }
  
  return new Uint8Array(bytes);
}

// Parse command line arguments
function parseArgs() {
  const args = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i].replace('--', '');
    const value = process.argv[i + 1];
    args[key] = value;
  }
  return args;
}

// Main execution
const parsedArgs = parseArgs();

// Validate required arguments
if (!parsedArgs.a || !parsedArgs.b || !parsedArgs.c) {
  console.error('Error: --a, --b, and --c are required');
  process.exit(1);
}

// Encode strings
const enc1 = b58encode(new TextEncoder().encode(parsedArgs.a));
const enc2 = b58encode(new TextEncoder().encode(parsedArgs.b));

// Decode string
const dec1 = b58decode(parsedArgs.c);

// Format output to match Python behavior exactly
console.log(`b'${enc1}'`);
console.log(`b'${enc2}'`);
const decodedString = new TextDecoder().decode(dec1);
console.log(`b'${decodedString}'`);