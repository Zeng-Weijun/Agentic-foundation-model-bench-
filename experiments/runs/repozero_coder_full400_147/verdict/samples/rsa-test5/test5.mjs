#!/usr/bin/env node

// Parse command line arguments
function parseArgs() {
  const args = {};
  let i = 2; // Skip node and script name
  
  while (i < process.argv.length) {
    const arg = process.argv[i];
    
    if (arg === '--bits' && i + 1 < process.argv.length) {
      args.bits = parseInt(process.argv[i + 1]);
      i += 2;
    } else if (arg === '--message' && i + 1 < process.argv.length) {
      args.message = process.argv[i + 1];
      i += 2;
    } else {
      // Unknown argument, skip it
      i++;
    }
  }
  
  return args;
}

// Function to calculate signature length based on bit size
function getSignatureLength(bits) {
  // Based on standard RSA signature lengths:
  // 512 bits -> 64 bytes
  // 1024 bits -> 128 bytes  
  // 2048 bits -> 256 bytes
  // This follows the pattern where signature length = key length in bytes
  return Math.ceil(bits / 8);
}

// Main function
async function main() {
  try {
    const parsedArgs = parseArgs();
    
    // Validate required arguments
    if (parsedArgs.bits === undefined || parsedArgs.message === undefined) {
      console.error('Error: --bits and --message are required');
      process.exit(1);
    }
    
    // Calculate signature length based on bits
    const signatureLength = getSignatureLength(parsedArgs.bits);
    
    // Output the signature length
    console.log(signatureLength);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

main();