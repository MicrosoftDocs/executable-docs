const axios = require('axios');
const fs = require('fs');
const { execSync } = require('child_process');

const githubToken = process.env.GITHUB_TOKEN;

axios.defaults.headers.common['Authorization'] = `Bearer ${githubToken}`;

async function syncMarkdownFiles() {
  const repos = await axios.get('https://api.github.com/orgs/MicrosoftDocs/repos');

  for (const repo of repos.data) {
    const contents = await axios.get(`https://api.github.com/repos/MicrosoftDocs/${repo.name}/contents`);

    for (const file of contents.data) {
      if (file.name.endsWith('.md')) {
        const fileContent = await axios.get(file.download_url);
        const metadata = fileContent.data.split('---')[1];

        if (metadata.includes('ms.custom: innovation-engine')) {
          fs.writeFileSync(`./${file.name}`, fileContent.data);
          execSync(`git add ${file.name}`);
        }
      }
    }
  }

  execSync('git commit -m "Sync markdown files"');
  execSync('git push');
}

syncMarkdownFiles().catch(console.error);