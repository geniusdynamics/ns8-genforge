# GenForge modules index for NS8

This is the official GenForge NS8 index of modules.

Metadata are built every 4 hours at 00:25, 06:25 ,12:25, 18:25 UTC and on each commit to the `main` branch.

If you want to add a module to this repository, just follow the
[instructions](https://nethserver.github.io/ns8-core/modules/new_module/#step-5-publish-to-ns8-software-repository)
for `ns8-repomd`, finally open the pull request here!

To use the modules listed here as NS8 repository, see the [manual
page](https://docs.nethserver.org/projects/ns8/en/latest/modules.html#software-repositories)
and set the following URL:

    https://forge.genius.ke/ns8/updates/

Alternative URL:

    https://raw.githubusercontent.com/geniusdynamics/ns8-genforge/repomd/ns8/updates/


Under settings, Chose Software Repository

![image](https://github.com/geniusdynamics/ns8-genforge/assets/16150798/512b9de4-cb81-44ab-9565-ce4f22e7c692)


Click on Add Repository
![image](https://github.com/geniusdynamics/ns8-genforge/assets/16150798/b8ca4b2d-7125-46fb-89fd-ad4d92fadb19)


Define the Repo URL as shown below with the Define URL
![image](https://github.com/geniusdynamics/ns8-genforge/assets/16150798/b05787f2-4184-4d0d-a805-7a159a1e8859)
Then CLick Add

**Enabling Testing Repo**

For testing Purposes, you may enable the testing Toggle.

Note that Apps installed with Testing Toggle enable may not be suitable for production


## Application List

All apps are sorted by categories and listed alphabetically. Click on the stars badge to visit the product's GitHub repository. Apps not yet listed but available in the Software Center can be added upon request. **Happy searching!**

<!-- BEGIN STARTUP LIST -->

| Category               | Company                                    | Description                                                                                     | GitHub Stars                                                                                                                                              | Alternative to                                                              | NS8link                                                                                                 |
|:-----------------------|:-------------------------------------------|:------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------:|:---------------------------------------------------------------------------:|:--------------------------------------------------------------------------------------------------------:|
| **Auth & SSO**         | [Zitadel](https://zitadel.com/)            | User authentication and session management framework                                            | [![GitHub Stars](https://img.shields.io/github/stars/zitadel/zitadel?style=social)](https://github.com/zitadel/zitadel)                                   | [Okta](https://okta.com/), [Auth0](https://auth0.com/)                      | [NS8link](https://github.com/geniusdynamics/ns8-zitadel/)                                              |
| **Auth & SSO**         | [Authentik](https://goauthentik.io/)            | User authentication and session management framework                                            | [![GitHub Stars](https://img.shields.io/github/stars/goauthentik/authentik?style=social)](https://github.com/goauthentik/authentik)                                   | [Okta](https://okta.com/), [Auth0](https://auth0.com/)                      | [NS8link](https://github.com/geniusdynamics/ns8-goauthentik/)                                              |
| **Backend as a Service**| [PocketBase](https://pocketbase.io/)      | Backend server with REST APIs to manage core backend needs                                       | [![GitHub Stars](https://img.shields.io/github/stars/pocketbase/pocketbase?style=social)](https://github.com/pocketbase/pocketbase)                       | [Firebase](https://firebase.google.com/)                                    | [NS8link](https://github.com/geniusdynamics/ns8-pocketbase/)                                           |
| **Design**             | [Penpot](https://penpot.app/)              | Design & prototyping platform                                                                    | [![GitHub Stars](https://img.shields.io/github/stars/penpot/penpot?style=social)](https://github.com/penpot/penpot)                                        | [Figma](https://www.figma.com/)                                             | [NS8link](https://github.com/geniusdynamics/ns8-penpot/)                                               |
| **Digital Signature**  | [DocuSeal](https://docuseal.co)            | Digital signing infrastructure                                                                   | [![GitHub Stars](https://img.shields.io/github/stars/docusealco/docuseal?style=social)](https://github.com/docusealco/docuseal)                           | [DocuSign](https://www.docusign.com/)                                       | [NS8link](https://github.com/geniusdynamics/ns8-docuseal/)                                             |
| **Digital Signature**  | [Documenso](https://documenso.com)         | Digital signing infrastructure                                                                   | [![GitHub Stars](https://img.shields.io/github/stars/documenso/documenso?style=social)](https://github.com/documenso/documenso)                           | [DocuSign](https://www.docusign.com/)                                       | [NS8link](https://github.com/geniusdynamics/ns8-documenso/)                                            |
| **ERP**                | [Dolibarr](https://www.dolibarr.org/)      | Business management suite (ERP and CRM)                                                          | [![GitHub Stars](https://img.shields.io/github/stars/Dolibarr/dolibarr?style=social)](https://github.com/Dolibarr/dolibarr)                               | [Oracle Fusion ERP](https://www.oracle.com/erp), [Odoo](https://odoo.com/) | [NS8link](https://github.com/geniusdynamics/ns8-dolibarr/)                                              |
| **ERP**                | [ERPNext](https://erpnext.com)             | Agile, modern, module-based business management suite                                            | [![GitHub Stars](https://img.shields.io/github/stars/frappe/erpnext?style=social)](https://github.com/frappe/erpnext)                                      | [SAP Business One](https://www.sap.com/products/business-one.html), [Odoo](https://odoo.com/) | [NS8link](https://github.com/geniusdynamics/ns8-erpnext/)                                              |
| **Email Marketing**    | [Keila](https://www.keila.io/)             | Email newsletter tool                                                                            | [![GitHub Stars](https://img.shields.io/github/stars/pentacent/keila?style=social)](https://github.com/pentacent/keila)                                    | [Mailchimp](https://mailchimp.com), [Sendinblue](https://www.sendinblue.com)| [NS8link](https://github.com/geniusdynamics/ns8-keila/)                                                |
| **File Hosting**       | [Filestash](https://www.filestash.app/)    | File manager that lets you manage your data anywhere                                             | [![GitHub Stars](https://img.shields.io/github/stars/mickael-kerjean/filestash?style=social)](https://github.com/mickael-kerjean/filestash)               | [Dropbox](https://www.dropbox.com/), [Google Drive](https://drive.google.com/) | [NS8link](https://github.com/geniusdynamics/ns8-filestash/)                                             |
| **File Hosting**       | [Nextcloud](https://nextcloud.com/)        | Personal cloud that runs on your own server                                                      | [![GitHub Stars](https://img.shields.io/github/stars/nextcloud/server?style=social)](https://github.com/nextcloud/server)                                  | [Dropbox](https://www.dropbox.com/), [Google Drive](https://drive.google.com/) | [NS8link](https://github.com/geniusdynamics/ns8-nextcloud/)                                             |
| **File Hosting**       | [Spacedrive](https://spacedrive.com/)      | Cross-platform file manager, powered by a virtual distributed filesystem (VDFS) written in Rust  | [![GitHub Stars](https://img.shields.io/github/stars/spacedriveapp/spacedrive?style=social)](https://github.com/spacedriveapp/spacedrive)                 | [Dropbox](https://www.dropbox.com/), [Google Drive](https://drive.google.com/) | [NS8link](https://github.com/geniusdynamics/ns8-spacedrive/)                                            |
| **Form Building**      | [Formbricks](https://formbricks.com/)      | Build forms and manage submission data in one platform                                           | [![GitHub Stars](https://img.shields.io/github/stars/formbricks/formbricks?style=social)](https://github.com/formbricks/formbricks)                       | [Typeform](https://www.typeform.com/), [Google Forms](https://forms.google.com), [React Hook Form](https://react-hook-form.com/) | [NS8link](https://github.com/geniusdynamics/ns8-formbricks/)                                            |
| **Form Building**      | [Formio](https://form.io/)                 | Form and data management platform for progressive web applications                               | [![GitHub Stars](https://img.shields.io/github/stars/formio/formio?style=social)](https://github.com/formio/formio)                                        | [Vueform](https://vueform.com/), [Typeform](https://www.typeform.com/)       | [NS8link](https://github.com/geniusdynamics/ns8-formio/)                                                |
| **Marketing SaaS**     | [Dub](https://dub.sh/)                     | Open-source Bitly alternative with built-in analytics                                            | [![GitHub Stars](https://img.shields.io/github/stars/steven-tey/dub?style=social)](https://github.com/steven-tey/dub)                                     | [Bitly](https://bitly.com/)                                                 | [NS8link](https://github.com/geniusdynamics/ns8-dub/)                                                   |
| **Messaging**          | [Element](https://element.io/)             | Enterprise communication platform                                                                | [![GitHub Stars](https://img.shields.io/github/stars/vector-im/element-web?style=social)](https://github.com/vector-im/element-web)                       | [Slack](https://slack.com/)                                                 | [NS8link](https://github.com/geniusdynamics/ns8-element/)                                               |
| **Messaging**          | [Mattermost](https://mattermost.com/)      | Enterprise communication platform for developers                                                 | [![GitHub Stars](https://img.shields.io/github/stars/mattermost/mattermost-server?style=social)](https://github.com/mattermost/mattermost-server)         | [Slack](https://slack.com/)                                                 | [NS8link](https://github.com/geniusdynamics/ns8-mattermost/)                                            |
| **Messaging**          | [Rocket.chat](https://rocket.chat/)        | Enterprise communication platform                                                                | [![GitHub Stars](https://img.shields.io/github/stars/RocketChat/Rocket.Chat?style=social)](https://github.com/RocketChat/Rocket.Chat)                     | [Slack](https://slack.com/)                                                 | [NS8link](https://github.com/geniusdynamics/ns8-rocketchat/)                                            |
| **No-code Database**   | [NocoDB](https://www.nocodb.com/)          | No-code database and Airtable alternative                                                        | [![GitHub Stars](https://img.shields.io/github/stars/nocodb/nocodb?style=social)](https://github.com/nocodb/nocodb)                                       | [Airtable](https://airtable.com/)                                           | [NS8link](https://github.com/geniusdynamics/ns8-nocodb/)                                                |
| **No-code Database**   | [Seatable](https://seatable.io/)           | Spreadsheet with database functionalities                                                         | [![GitHub Stars](https://img.shields.io/github/stars/seatable/seatable?style=social)](https://github.com/seatable/seatable)                               | [Airtable](https://airtable.com/)                                           | [NS8link](https://github.com/geniusdynamics/ns8-seatable/)                                              |
| **Notetaking**         | [Logseq](https://logseq.com/)              | Platform for knowledge management, note-taking, and task management                              | [![GitHub Stars](https://img.shields.io/github/stars/logseq/logseq?style=social)](https://github.com/logseq/logseq)                                       | [Evernote](https://evernote.com/), [OneNote](https://www.onenote.com/), [Roam Research](https://roamresearch.com/) | [NS8link](https://github.com/geniusdynamics/ns8-logseq/)                                                |
| **Notetaking**         | [Outline](https://www.getoutline.com/)     | Wiki and knowledge base                                                                          | [![GitHub Stars](https://img.shields.io/github/stars/outline/outline?style=social)](https://github.com/outline/outline)                                   | [Notion](https://notion.so)                                                 | [NS8link](https://github.com/geniusdynamics/ns8-outline/)                                               |
| **Password Manager**   | [VaultWarden](https://vaultwarden.co/)     | Password manager for teams and individuals                                                       | [![GitHub Stars](https://img.shields.io/github/stars/dani-garcia/vaultwarden?style=social)](https://github.com/dani-garcia/vaultwarden)                   | [1Password](https://1password.com/)                                         | [NS8link](https://github.com/geniusdynamics/ns8-vaultwarden/)                                           |
| **PaaS**               | [Coolify](https://coolify.io/)             | Self-hostable Heroku alternative                                                                 | [![GitHub Stars](https://img.shields.io/github/stars/coollabsio/coolify?style=social)](https://github.com/coollabsio/coolify)                             | [Heroku](https://www.heroku.com/)                                           | [NS8link](https://github.com/geniusdynamics/ns8-coolify/)                                               |
| **Project Management** | [Plane](https://plane.so/)                 | Alternative to Linear, JIRA, Trello, and Height                                                  | [![GitHub Stars](https://img.shields.io/github/stars/makeplane/plane?style=social)](https://github.com/makeplane/plane)                                   | [Linear](https://linear.app/), [JIRA](https://www.atlassian.com/software/jira), [Trello](https://trello.com/), [Height](https://height.app/) | [NS8link](https://github.com/geniusdynamics/ns8-plane/)                                                 |
| **Project Management** | [Taiga](https://www.taiga.io/)             | Project management software                                                                      | [![GitHub Stars](https://img.shields.io/github/stars/kaleidos-ventures/taiga-docker?style=social)](https://github.com/kaleidos-ventures/taiga-docker)     | [Asana](https://asana.com/), [Trello](https://trello.com/), [JIRA](https://www.atlassian.com/software/jira) | [NS8link](https://github.com/geniusdynamics/ns8-taiga/)                                                  |
| **Project Management** | [Vikunja](https://vikunja.io/)             | To-do app to organize your next project                                                          | [![GitHub Stars](https://img.shields.io/github/stars/go-vikunja/api?style=social)](https://github.com/go-vikunja/api)                                     | [Todoist](https://todoist.com), [Trello](https://trello.com), [Asana](https://asana.com) | [NS8link](https://github.com/geniusdynamics/ns8-vikunja/)                                                |
| **Scheduling**         | [Cal.com](https://cal.com/)                | Scheduling infrastructure, alternative to Calendly                                               | [![GitHub Stars](https://img.shields.io/github/stars/calendso/calendso?style=social)](https://github.com/calendso/calendso)                               | [Calendly](https://calendly.com/)                                           | [NS8link](https://github.com/geniusdynamics/ns8-cal/)                                                   |
| **Video Conferencing** | [Jitsi](https://jitsi.org/meet)            | Video conferences platform and SDK                                                               | [![GitHub Stars](https://img.shields.io/github/stars/jitsi/jitsi-meet?style=social)](https://github.com/jitsi/jitsi-meet)                                 | [Zoom](https://zoom.us/)                                                    | [NS8link](https://github.com/geniusdynamics/ns8-jitsi/)                                                 |
| **Video Conferencing** | [LiveKit](https://livekit.io/)             | SFU and SDKs for high-performance, scalable WebRTC                                               | [![GitHub Stars](https://img.shields.io/github/stars/livekit/livekit-server?style=social)](https://github.com/livekit/livekit-server)                     | [Twilio](https://www.twilio.com/), [Agora](https://agora.io/)               | [NS8link](https://github.com/geniusdynamics/ns8-livekit/)                                               |
| **Web Analytics**      | [Matomo](https://matomo.org/)              | Google Analytics alternative                                                                     | [![GitHub Stars](https://img.shields.io/github/stars/matomo-org/matomo?style=social)](https://github.com/matomo-org/matomo)                               | [Google Analytics](https://analytics.google.com/)                           | [NS8link](https://github.com/geniusdynamics/ns8-matomo/)                                                |
| **Web Analytics**      | [Plausible](https://plausible.io/)         | Google Analytics alternative                                                                     | [![GitHub Stars](https://img.shields.io/github/stars/plausible/analytics?style=social)](https://github.com/plausible/analytics)                           | [Google Analytics](https://analytics.google.com/)                           | [NS8link](https://github.com/geniusdynamics/ns8-plausible/)                                             |
| **Web Analytics**      | [Swetrix](https://swetrix.com)             | Google Analytics alternative                                                                     | [![GitHub Stars](https://img.shields.io/github/stars/Swetrix/swetrix-api?style=social)](https://github.com/Swetrix/swetrix-api)                           | [Google Analytics](https://analytics.google.com/)                           | [NS8link](https://github.com/geniusdynamics/ns8-swetrix/)                                               |
| **Web Analytics**      | [Umami](https://umami.is)                  | Google Analytics alternative                                                                     | [![GitHub Stars](https://img.shields.io/github/stars/mikecao/umami?style=social)](https://github.com/mikecao/umami)                                       | [Google Analytics](https://analytics.google.com/)                           | [NS8link](https://github.com/geniusdynamics/ns8-umami/)                                                 |
| **Workflow Automation**| [Activepieces](https://www.activepieces.com) | No-code business automation tool                                                                | [![GitHub Stars](https://img.shields.io/github/stars/activepieces/activepieces?style=social)](https://github.com/activepieces/activepieces)               | [Zapier](https://www.zapier.com/), [Tray](https://tray.io/)                 | [NS8link](https://github.com/geniusdynamics/ns8-activepieces/)                                          |
| **Workflow Automation**| [N8N](https://n8n.io/)                    | Node-based workflow automation tool for developers                                               | [![GitHub Stars](https://img.shields.io/github/stars/n8n-io/n8n?style=social)](https://github.com/n8n-io/n8n)                                             | [Zapier](https://zapier.com/)                                               | [NS8link](https://github.com/geniusdynamics/ns8-n8n/)                                                   |
| **Workflow Automation**| [Pipedream](https://pipedream.com/)       | Workflow automation and API integration platform                                                 | [![GitHub Stars](https://img.shields.io/github/stars/PipedreamHQ/pipedream?style=social)](https://github.com/PipedreamHQ/pipedream)                       | [Zapier](https://zapier.com/), [Integromat](https://www.integromat.com/)    | [NS8link](https://github.com/geniusdynamics/ns8-pipedream/)                                              |
| **Workflow Automation**| [Temporal](https://temporal.io/)          | Workflows as code platform                                                                       | [![GitHub Stars](https://img.shields.io/github/stars/temporalio/temporal?style=social)](https://github.com/temporalio/temporal)                           | [Airflow](https://airflow.apache.org/), [AWS Step Functions](https://aws.amazon.com/step-functions/) | [NS8link](https://github.com/geniusdynamics/ns8-temporal/)                                              |

<!-- END STARTUP LIST -->



