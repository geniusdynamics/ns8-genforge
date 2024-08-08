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

All Apps in the list are sorted by categories and sorted in alphabetical order. If you click on the stars badge you will get to the product's repo. 
Some Apps are listed and not available yet, MEaning they are coming or still in development.

For those not yet Listed and are available in the Software Center, Contact Us to List them
**Have a good search!**

<!-- BEGIN STARTUP LIST -->

|Category|Company|Description|GitHub Stars|Alternative to|
|:-------|:------|:----------|:----------:|:------------:|

Auth & SSO|[Zitadel](https://zitadel.com/)|User authentication and session management framework|<a href=https://github.com/zitadel/zitadel><img src="https://img.shields.io/github/stars/zitadel/zitadel?style=social" width=150/></a>|[Okta](https://okta.com/), [Auth0](https://auth0.com/)|
Backend as a service|[PocketBase](https://pocketbase.io/)|Backend server with REST APIs to manage core backend needs|<a href=https://github.com/pocketbase/pocketbase><img src="https://img.shields.io/github/stars/pocketbase/pocketbase?style=social" width=150/></a>|[Firebase](https://firebase.google.com/)|
Design|[Penpot](https://penpot.app/)|Design & prototyping platform|<a href=https://github.com/penpot/penpot><img src="https://img.shields.io/github/stars/penpot/penpot?style=social" width=150/></a>|[Figma](https://www.figma.com/)|
Digital Signature|[DocuSeal](https://docuseal.co)|Digital Signing Infrastructure|<a href=https://github.com/docusealco/docuseal><img src="https://img.shields.io/github/stars/docusealco/docuseal?style=social" width=150/></a>|[DocuSign](https://www.docusign.com/)|
Digital Signature|[Documenso](https://documenso.com)|Digital Signing Infrastructure|<a href=https://github.com/documenso/documenso><img src="https://img.shields.io/github/stars/documenso/documenso?style=social" width=150/></a>|[DocuSign](https://www.docusign.com/)|
ERP|[Dolibarr](https://www.dolibarr.org/) | Business management suite (ERP and CRM)|<a href=https://github.com/Dolibarr/dolibarr><img src="https://img.shields.io/github/stars/Dolibarr/dolibarr?style=social" width=150/></a>|[Oracle Fusion ERP Cloud](https://www.oracle.com/erp),[Odoo](https://odoo.com/),[Microsoft Dynamics](https://dynamics.microsoft.com/)
ERP|[ERPNext](https://erpnext.com) | Agile, modern, module based Business management suite|<a href=https://github.com/frappe/erpnext><img src="https://img.shields.io/github/stars/frappe/erpnext?style=social" width=150/>|[SAP Business One](https://www.sap.com/products/business-one.html), [Odoo](https://odoo.com/)|
Email marketing|[Keila](https://www.keila.io/)|Email newsletter tool|<a href=https://github.com/pentacent/keila><img src="https://img.shields.io/github/stars/pentacent/keila?style=social" width=150/></a>|[Mailchimp](https://mailchimp.com), [Sendinblue](https://www.sendinblue.com)|
File Hosting|[Filestash](https://www.filestash.app/)|A file manager that let you manage your data anywhere it is located|<a href=https://github.com/mickael-kerjean/filestash><img src="https://img.shields.io/github/stars/mickael-kerjean/filestash?style=social" width=150/></a>|[Dropbox](https://www.dropbox.com/), [Google Drive](https://drive.google.com/)|
File Hosting|[Nextcloud](https://nextcloud.com/)|A personal cloud which runs on your own server|<a href=https://github.com/nextcloud/server><img src="https://img.shields.io/github/stars/nextcloud/server?style=social" width=150/></a>|[Dropbox](https://www.dropbox.com/), [Google Drive](https://drive.google.com/)|
File Hosting|[Spacedrive](https://spacedrive.com/)|Cross-platform file manager, powered by a virtual distributed filesystem (VDFS) written in Rust|<a href=https://github.com/spacedriveapp/spacedrive><img src="https://img.shields.io/github/stars/spacedriveapp/spacedrive?style=social" width=150/></a>|[Dropbox](https://www.dropbox.com/), [Google Drive](https://drive.google.com/)|
Form Building|[Formbricks](https://formbricks.com/)| Build forms and receive & manage submission data in one platform |<a href=https://github.com/formbricks/formbricks><img src="https://img.shields.io/github/stars/formbricks/formbricks?style=social" width=150></a>|[Typeform](https://www.typeform.com/), [Google Forms](https://forms.google.com), [React Hook Form](https://react-hook-form.com/)
Form Building|[Formio](https://form.io/)| A Form and Data Management Platform for Progressive Web Applications|<a href=https://github.com/formio/formio><img src="https://img.shields.io/github/stars/formio/formio?style=social" width=150></a>|[Vueform](https://vueform.com/),[Typeform](https://www.typeform.com/)|
Marketing SaaS|[Dub](https://dub.sh/)|Open-source Bitly Alternative with built-in analytics|<a href=https://github.com/steven-tey/dub><img src="https://img.shields.io/github/stars/steven-tey/dub?style=social" width=150/></a>|[Bitly](https://bitly.com/)
Messaging|[Element](https://element.io/)|Enterprise communication platform|<a href=https://github.com/vector-im/element-web><img src="https://img.shields.io/github/stars/vector-im/element-web?style=social" width=150/></a>|[Slack](https://slack.com/)|
Messaging|[Mattermost](https://mattermost.com/)|Enterprise communication platform for developers|<a href=https://github.com/mattermost/mattermost-server><img src="https://img.shields.io/github/stars/mattermost/mattermost-server?style=social" width=150/></a>|[Slack](https://slack.com/)|
Messaging|[Rocket.chat](https://rocket.chat/)|Enterprise communication platform|<a href=https://github.com/RocketChat/Rocket.Chat><img src="https://img.shields.io/github/stars/RocketChat/Rocket.Chat?style=social" width=150/></a>|[Slack](https://slack.com/)|
No-code database|[NocoDB](https://www.nocodb.com/)|No-code database and Airtable alternative|<a href=https://github.com/nocodb/nocodb><img src="https://img.shields.io/github/stars/nocodb/nocodb?style=social" width=150/></a>|[AirTable](https://www.airtable.com/)
No-code database|[Rowy](https://www.rowy.io/)|Extendable Airtable-like spreadsheet UI for databases|<a href=https://github.com/rowyio/rowy><img src="https://img.shields.io/github/stars/rowyio/rowy?style=social" width=150/></a>|[AirTable](https://www.airtable.com/)|
No-code database|[Totum](https://totum.online/)|Business database for non-programmers|<a href=https://github.com/totumonline/totum-mit><img src="https://img.shields.io/github/stars/totumonline/totum-mit?style=social" width=150/></a>|[AirTable](https://www.airtable.com/)|
Notetaking|[AppFlowy](https://www.appflowy.io/)|Open-source alternative to Notion|<a href=https://github.com/AppFlowy-IO/appflowy><img src="https://img.shields.io/github/stars/AppFlowy-IO/appflowy?style=social" width=150/></a>|[Notion](https://www.notion.so/)
Notetaking|[Joplin](https://joplinapp.org/)|Secure, Cross-platform, Open-Source  Markdown Note Taking App|<a href=https://github.com/laurent22/joplin><img src="https://img.shields.io/github/stars/laurent22/joplin?style=social" width=150/></a>|[Evernote](https://evernote.com/), [Onenote](hhttps://www.onenote.com/n), [Roam Research](https://roamresearch.com/)|
Notetaking|[Outline](https://www.getoutline.com/)|Wiki and knowledge base|<a href=https://github.com/outline/outline><img src="https://img.shields.io/github/stars/outline/outline?style=social" width=150/></a>|[Notion](https://notion.so)|
Password manager|[VAultWarden](https://github.com/dani-garcia/vaultwarden)|Password manager for teams and individuals|<a href=https://github.com/dani-garcia/vaultwarden><img src="https://img.shields.io/github/stars/dani-garcia/vaultwarden?style=social" width=150/></a>|[1Password](https://1password.com/)
Platform as a service|[Coolify](https://coolify.io/)|Self-hostable Heroku alternative|<a href=https://github.com/coollabsio/coolify><img src="https://img.shields.io/github/stars/coollabsio/coolify?style=social" width=150/></a>|[Heroku](https://www.heroku.com/)|
Project Management|[Plane](https://plane.so/)|Alternative to Linear, JIRA, Trello and Height|<a href=https://github.com/makeplane/plane><img src="https://img.shields.io/github/stars/makeplane/plane?style=social" width=150/></a>|[Linear](https://linear.app/), [JIRA](https://www.atlassian.com/software/jira), [Trello](https://trello.com/), [Height](https://height.app/)|
Project Management|[Taiga](https://www.taiga.io/)|Project management software|<a href=https://github.com/kaleidos-ventures/taiga-docker><img src="https://img.shields.io/github/stars/kaleidos-ventures/taiga-docker?style=social" width=150/></a>|[Asana](https://asana.com/), [Trello](https://trello.com/), [Jira](https://www.atlassian.com/software/jira)|
Project Management|[Vikunja](https://vikunja.io/)|The to-do app to organize your next project.|<a href=https://github.com/go-vikunja/api><img src="https://img.shields.io/github/stars/go-vikunja/api?style=social" width=150/></a>|[Todoist](https://todoist.com), [Trello](https://trello.com), [Asana](https://asana.com)|
Scheduling|[Cal.com](https://cal.com/)|Scheduling infrastructure, alternative to Calendly|<a href=https://github.com/calendso/calendso><img src="https://img.shields.io/github/stars/calendso/calendso?style=social" width=150/></a>|[Calendly](https://calendly.com/)|
Video Conferencing|[Jitsi](https://jitsi.org/meet)|Video conferences platform and SDK|<a href=https://github.com/jitsi/jitsi-meet><img src="https://img.shields.io/github/stars/jitsi/jitsi-meet?style=social" width=150/></a>|[Zoom](https://zoom.us/)|
Video Conferencing|[LiveKit](https://livekit.io/)|SFU and SDKs for high-performance, scalable WebRTC|<a href=https://github.com/livekit/livekit-server><img src="https://img.shields.io/github/stars/livekit/livekit-server?style=social" width=150/></a>|[Twilio](https://www.twilio.com/), [Agora](https://agora.io/)|
Website analytics|[Matomo](https://matomo.org/)|Google Analytics alternative|<a href=https://github.com/matomo-org/matomo><img src="https://img.shields.io/github/stars/matomo-org/matomo?style=social" width=150/></a>|[Google Analytics](https://analytics.google.com/)
Website analytics|[Plausible](https://plausible.io/)|Google Analytics alternative|<a href=https://github.com/plausible/analytics><img src="https://img.shields.io/github/stars/plausible/analytics?style=social" width=150/></a>|[Google Analytics](https://analytics.google.com/)
Website analytics|[Swetrix](https://swetrix.com)|Google Analytics alternative|<a href=https://github.com/Swetrix/swetrix-api><img src="https://img.shields.io/github/stars/swetrix/swetrix-api?style=social" width=150/></a>|[Google Analytics](https://analytics.google.com/)|
Website analytics|[Umami](https://umami.is)|Google Analytics alternative|<a href=https://github.com/mikecao/umami><img src="https://img.shields.io/github/stars/mikecao/umami?style=social" width=150/></a>|[Google Analytics](https://analytics.google.com/)
Workflow automation| [Activepieces](https://www.activepieces.com) | No-code business automation tool |<a href=https://github.com/activepieces/activepieces><img src="https://img.shields.io/github/stars/activepieces/activepieces?style=social" width=150/></a> |[Zapier](https://www.zapier.com/), [Tray](https://tray.io/)
Workflow automation|[N8N](https://n8n.io/)|Node-based workflow automation tool for developers|<a href=https://github.com/n8n-io/n8n><img src="https://img.shields.io/github/stars/n8n-io/n8n?style=social" width=150/></a>|[Zapier](https://zapier.com/)
Workflow automation|[Pipedream](https://pipedream.com/)|Workflow automation and API integration platform|<a href=https://github.com/PipedreamHQ/pipedream><img src="https://img.shields.io/github/stars/PipedreamHQ/pipedream?style=social" width=150/></a>|[Zapier](https://zapier.com/), [Integromat](https://www.integromat.com/)|
Workflow automation|[Temporal](https://temporal.io/)|Workflows as code platform|<a href=https://github.com/temporalio/temporal><img src="https://img.shields.io/github/stars/temporalio/temporal?style=social" width=150/></a>|[Zapier](https://zapier.com/)

<!-- END STARTUP LIST -->

