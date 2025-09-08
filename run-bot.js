const { spawn } = require('child_process');

function startBot() {
  console.log('Starting Tibia Hunt Bot...');
  
  const botProcess = spawn('node', ['index.js'], {
    stdio: 'inherit'
  });

  botProcess.on('close', (code) => {
    if (code !== 0) {
      console.log(`Bot crashed with code ${code}. Restarting in 5 seconds...`);
      setTimeout(startBot, 5000);
    }
  });

  botProcess.on('error', (error) => {
    console.error('Bot error:', error);
    setTimeout(startBot, 5000);
  });
}

startBot();
