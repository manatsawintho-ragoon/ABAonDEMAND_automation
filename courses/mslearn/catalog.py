from courses.mslearn.base_config import MSLearnCourseConfig, MSLearnModuleConfig

# WEB101: only 2 modules verified working (others redirect to /training/browse/)
WEB101_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_WEB101',
    display_name='MS Learn — Web Development for Beginners',
    modules=[
        MSLearnModuleConfig(
            module_id='web-development-101-accessibility',
            title='Learn the basics of web accessibility',
            url='https://learn.microsoft.com/en-us/training/modules/web-development-101-accessibility/'
        ),
        MSLearnModuleConfig(
            module_id='web-development-101-conditional',
            title='Make decisions with JavaScript',
            url='https://learn.microsoft.com/en-us/training/modules/web-development-101-conditional/'
        ),
    ]
)

# GitHub core: all 4 verified working
GITHUB_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_GITHUB_GIT',
    display_name='MS Learn — Git & GitHub Fundamentals',
    modules=[
        MSLearnModuleConfig(
            module_id='intro-to-git',
            title='Introduction to Git',
            url='https://learn.microsoft.com/en-us/training/modules/intro-to-git/'
        ),
        MSLearnModuleConfig(
            module_id='introduction-to-github',
            title='Introduction to GitHub',
            url='https://learn.microsoft.com/en-us/training/modules/introduction-to-github/'
        ),
        MSLearnModuleConfig(
            module_id='github-introduction-products',
            title="Introduction to GitHub's products",
            url='https://learn.microsoft.com/en-us/training/modules/github-introduction-products/'
        ),
        MSLearnModuleConfig(
            module_id='github-introduction-administration',
            title='Introduction to GitHub administration',
            url='https://learn.microsoft.com/en-us/training/modules/github-introduction-administration/'
        ),
    ]
)

# GitHub Advanced: verified working (fixed settle→resolve merge conflicts slug)
GITHUB_ADVANCED_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_GH_ADVANCED',
    display_name='MS Learn — Manage Source Control with GitHub',
    modules=[
        MSLearnModuleConfig(
            module_id='maintain-secure-repository-github',
            title='Maintain a secure repository by using GitHub best practices',
            url='https://learn.microsoft.com/en-us/training/modules/maintain-secure-repository-github/'
        ),
        MSLearnModuleConfig(
            module_id='manage-changes-pull-requests-github',
            title='Manage repository changes by using pull requests on GitHub',
            url='https://learn.microsoft.com/en-us/training/modules/manage-changes-pull-requests-github/'
        ),
        MSLearnModuleConfig(
            module_id='search-organize-repository-history-github',
            title='Search and organize repository history by using GitHub',
            url='https://learn.microsoft.com/en-us/training/modules/search-organize-repository-history-github/'
        ),
        MSLearnModuleConfig(
            module_id='resolve-merge-conflicts-github',
            title='Resolve merge conflicts',
            url='https://learn.microsoft.com/en-us/training/modules/resolve-merge-conflicts-github/'
        ),
        MSLearnModuleConfig(
            module_id='contribute-open-source',
            title='Contribute to an open-source project on GitHub',
            url='https://learn.microsoft.com/en-us/training/modules/contribute-open-source/'
        ),
        MSLearnModuleConfig(
            module_id='manage-innersource-program-github',
            title='Manage an InnerSource program by using GitHub',
            url='https://learn.microsoft.com/en-us/training/modules/manage-innersource-program-github/'
        ),
    ]
)

# GitHub Actions: all 5 verified working
GITHUB_ACTIONS_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_GH_ACTIONS',
    display_name='MS Learn — Automate with GitHub Actions',
    modules=[
        MSLearnModuleConfig(
            module_id='introduction-to-github-actions',
            title='Introduction to GitHub Actions',
            url='https://learn.microsoft.com/en-us/training/modules/introduction-to-github-actions/'
        ),
        MSLearnModuleConfig(
            module_id='github-actions-automate-tasks',
            title='Automate development tasks by using GitHub Actions',
            url='https://learn.microsoft.com/en-us/training/modules/github-actions-automate-tasks/'
        ),
        MSLearnModuleConfig(
            module_id='github-actions-ci',
            title='Build continuous integration (CI) workflows by using GitHub Actions',
            url='https://learn.microsoft.com/en-us/training/modules/github-actions-ci/'
        ),
        MSLearnModuleConfig(
            module_id='github-actions-cd',
            title='Implement a code workflow in your build pipeline by using Git and GitHub',
            url='https://learn.microsoft.com/en-us/training/modules/github-actions-cd/'
        ),
        MSLearnModuleConfig(
            module_id='manage-github-actions-enterprise',
            title='Manage GitHub Actions in the enterprise',
            url='https://learn.microsoft.com/en-us/training/modules/manage-github-actions-enterprise/'
        ),
    ]
)

# GitHub Copilot: all 5 verified working
GITHUB_COPILOT_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_COPILOT',
    display_name='MS Learn — GitHub Copilot Fundamentals',
    modules=[
        MSLearnModuleConfig(
            module_id='introduction-to-github-copilot',
            title='Introduction to GitHub Copilot',
            url='https://learn.microsoft.com/en-us/training/modules/introduction-to-github-copilot/'
        ),
        MSLearnModuleConfig(
            module_id='introduction-to-prompt-engineering-with-github-copilot',
            title='Introduction to prompt engineering with GitHub Copilot',
            url='https://learn.microsoft.com/en-us/training/modules/introduction-to-prompt-engineering-with-github-copilot/'
        ),
        MSLearnModuleConfig(
            module_id='using-github-copilot-with-javascript',
            title='Using GitHub Copilot with JavaScript',
            url='https://learn.microsoft.com/en-us/training/modules/using-github-copilot-with-javascript/'
        ),
        MSLearnModuleConfig(
            module_id='using-github-copilot-with-python',
            title='Using GitHub Copilot with Python',
            url='https://learn.microsoft.com/en-us/training/modules/using-github-copilot-with-python/'
        ),
        MSLearnModuleConfig(
            module_id='github-copilot-across-environments',
            title='Leverage GitHub Copilot tools for enterprise development',
            url='https://learn.microsoft.com/en-us/training/modules/github-copilot-across-environments/'
        ),
    ]
)

# Python: only 3 modules verified working (rest redirect to /training/browse/)
PYTHON_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_PYTHON',
    display_name='MS Learn — Python for Beginners',
    modules=[
        MSLearnModuleConfig(
            module_id='python-variables',
            title='Use variables and data in Python',
            url='https://learn.microsoft.com/en-us/training/modules/python-variables/'
        ),
        MSLearnModuleConfig(
            module_id='python-files',
            title='Work with files and directories in Python',
            url='https://learn.microsoft.com/en-us/training/modules/python-files/'
        ),
        MSLearnModuleConfig(
            module_id='python-packages-environments',
            title='Manage packages and virtual environments in Python',
            url='https://learn.microsoft.com/en-us/training/modules/python-packages-environments/'
        ),
    ]
)

# C#: all 8 verified working
CSHARP_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_CSHARP',
    display_name='MS Learn — C# Foundational',
    modules=[
        MSLearnModuleConfig(
            module_id='csharp-write-first-code',
            title='Write your first C# code',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-write-first-code/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-literals-variables',
            title='Store and retrieve data using literal and variable values in C#',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-literals-variables/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-basic-formatting',
            title='Perform basic string formatting in C#',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-basic-formatting/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-readable-code',
            title='Write clean, readable C# code',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-readable-code/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-if-elseif-else',
            title='Add decision logic to your code using if, elseif, and else in C#',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-if-elseif-else/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-arrays',
            title='Store and iterate through sequences of data using Arrays and the foreach in C#',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-arrays/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-code-blocks',
            title='Create readable code with conventions, allowlists, and comments',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-code-blocks/'
        ),
        MSLearnModuleConfig(
            module_id='csharp-convert-cast',
            title='Convert data types using casting and conversion techniques in C#',
            url='https://learn.microsoft.com/en-us/training/modules/csharp-convert-cast/'
        ),
    ]
)

# AZ-900: all 11 verified working
AZURE_FUNDAMENTALS_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_AZ900',
    display_name='MS Learn — Azure Fundamentals (AZ-900)',
    modules=[
        MSLearnModuleConfig(
            module_id='describe-cloud-compute',
            title='Describe cloud computing',
            url='https://learn.microsoft.com/en-us/training/modules/describe-cloud-compute/'
        ),
        MSLearnModuleConfig(
            module_id='describe-benefits-use-cloud-services',
            title='Describe the benefits of using cloud services',
            url='https://learn.microsoft.com/en-us/training/modules/describe-benefits-use-cloud-services/'
        ),
        MSLearnModuleConfig(
            module_id='describe-cloud-service-types',
            title='Describe cloud service types',
            url='https://learn.microsoft.com/en-us/training/modules/describe-cloud-service-types/'
        ),
        MSLearnModuleConfig(
            module_id='describe-core-architectural-components-of-azure',
            title='Describe the core architectural components of Azure',
            url='https://learn.microsoft.com/en-us/training/modules/describe-core-architectural-components-of-azure/'
        ),
        MSLearnModuleConfig(
            module_id='describe-azure-compute-networking-services',
            title='Describe Azure compute and networking services',
            url='https://learn.microsoft.com/en-us/training/modules/describe-azure-compute-networking-services/'
        ),
        MSLearnModuleConfig(
            module_id='describe-azure-storage-services',
            title='Describe Azure storage services',
            url='https://learn.microsoft.com/en-us/training/modules/describe-azure-storage-services/'
        ),
        MSLearnModuleConfig(
            module_id='describe-azure-identity-access-security',
            title='Describe Azure identity, access, and security',
            url='https://learn.microsoft.com/en-us/training/modules/describe-azure-identity-access-security/'
        ),
        MSLearnModuleConfig(
            module_id='describe-cost-management-azure',
            title='Describe cost management in Azure',
            url='https://learn.microsoft.com/en-us/training/modules/describe-cost-management-azure/'
        ),
        MSLearnModuleConfig(
            module_id='describe-features-tools-azure-for-governance-compliance',
            title='Describe features and tools in Azure for governance and compliance',
            url='https://learn.microsoft.com/en-us/training/modules/describe-features-tools-azure-for-governance-compliance/'
        ),
        MSLearnModuleConfig(
            module_id='describe-features-tools-manage-deploy-azure-resources',
            title='Describe features and tools for managing and deploying Azure resources',
            url='https://learn.microsoft.com/en-us/training/modules/describe-features-tools-manage-deploy-azure-resources/'
        ),
        MSLearnModuleConfig(
            module_id='describe-monitoring-tools-azure',
            title='Describe monitoring tools in Azure',
            url='https://learn.microsoft.com/en-us/training/modules/describe-monitoring-tools-azure/'
        ),
    ]
)

# AI-900: 4 verified working + fundamentals-machine-learning (removed 8 broken modules)
AI_FUNDAMENTALS_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_AI900',
    display_name='MS Learn — AI Fundamentals (AI-900)',
    modules=[
        MSLearnModuleConfig(
            module_id='get-started-ai-fundamentals',
            title='Get started with AI on Azure',
            url='https://learn.microsoft.com/en-us/training/modules/get-started-ai-fundamentals/'
        ),
        MSLearnModuleConfig(
            module_id='fundamentals-machine-learning',
            title='Fundamentals of machine learning',
            url='https://learn.microsoft.com/en-us/training/modules/fundamentals-machine-learning/'
        ),
        MSLearnModuleConfig(
            module_id='fundamentals-generative-ai',
            title='Fundamentals of Generative AI',
            url='https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/'
        ),
        MSLearnModuleConfig(
            module_id='recognize-synthesize-speech',
            title='Recognize and synthesize speech',
            url='https://learn.microsoft.com/en-us/training/modules/recognize-synthesize-speech/'
        ),
    ]
)

# PowerBI: only 3 verified working (removed 4 broken modules)
POWERBI_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_POWERBI',
    display_name='MS Learn — Power BI Data Analyst',
    modules=[
        MSLearnModuleConfig(
            module_id='get-started-with-power-bi',
            title='Get started building with Power BI',
            url='https://learn.microsoft.com/en-us/training/modules/get-started-with-power-bi/'
        ),
        MSLearnModuleConfig(
            module_id='get-data',
            title='Get data in Power BI',
            url='https://learn.microsoft.com/en-us/training/modules/get-data/'
        ),
        MSLearnModuleConfig(
            module_id='clean-data-power-bi',
            title='Clean, transform, and load data in Power BI',
            url='https://learn.microsoft.com/en-us/training/modules/clean-data-power-bi/'
        ),
    ]
)

# SC-900: all 8 verified working
SECURITY_FUNDAMENTALS_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_SC900',
    display_name='MS Learn — Security, Compliance, and Identity Fundamentals (SC-900)',
    modules=[
        MSLearnModuleConfig(
            module_id='describe-security-concepts-methodologies',
            title='Describe security and compliance concepts',
            url='https://learn.microsoft.com/en-us/training/modules/describe-security-concepts-methodologies/'
        ),
        MSLearnModuleConfig(
            module_id='describe-identity-principles-concepts',
            title='Describe identity concepts',
            url='https://learn.microsoft.com/en-us/training/modules/describe-identity-principles-concepts/'
        ),
        MSLearnModuleConfig(
            module_id='explore-basic-services-identity-types',
            title='Describe the basic services and identity types of Azure AD',
            url='https://learn.microsoft.com/en-us/training/modules/explore-basic-services-identity-types/'
        ),
        MSLearnModuleConfig(
            module_id='explore-authentication-capabilities',
            title='Describe the authentication capabilities of Azure AD',
            url='https://learn.microsoft.com/en-us/training/modules/explore-authentication-capabilities/'
        ),
        MSLearnModuleConfig(
            module_id='explore-access-management-capabilities',
            title='Describe the access management capabilities of Azure AD',
            url='https://learn.microsoft.com/en-us/training/modules/explore-access-management-capabilities/'
        ),
        MSLearnModuleConfig(
            module_id='describe-basic-cybersecurity-threats-attacks-mitigations',
            title='Describe threat protection with Microsoft 365 Defender',
            url='https://learn.microsoft.com/en-us/training/modules/describe-basic-cybersecurity-threats-attacks-mitigations/'
        ),
        MSLearnModuleConfig(
            module_id='describe-security-management-capabilities-of-azure',
            title='Describe security management capabilities of Azure',
            url='https://learn.microsoft.com/en-us/training/modules/describe-security-management-capabilities-of-azure/'
        ),
        MSLearnModuleConfig(
            module_id='describe-compliance-management-capabilities-microsoft',
            title='Describe the compliance management capabilities in Microsoft Purview',
            url='https://learn.microsoft.com/en-us/training/modules/describe-compliance-management-capabilities-microsoft/'
        ),
    ]
)

# T-SQL: all 6 modules from "Query and modify data with T-SQL" learning path verified
TSQL_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_TSQL',
    display_name='MS Learn — Transact-SQL (T-SQL) Fundamentals',
    modules=[
        MSLearnModuleConfig(
            module_id='introduction-to-transact-sql',
            title='Introduction to Transact-SQL',
            url='https://learn.microsoft.com/en-us/training/modules/introduction-to-transact-sql/'
        ),
        MSLearnModuleConfig(
            module_id='sort-filter-queries',
            title='Sort and filter results in T-SQL',
            url='https://learn.microsoft.com/en-us/training/modules/sort-filter-queries/'
        ),
        MSLearnModuleConfig(
            module_id='query-multiple-tables-with-joins',
            title='Combine multiple tables with JOINs in T-SQL',
            url='https://learn.microsoft.com/en-us/training/modules/query-multiple-tables-with-joins/'
        ),
        MSLearnModuleConfig(
            module_id='write-subqueries',
            title='Write Subqueries in T-SQL',
            url='https://learn.microsoft.com/en-us/training/modules/write-subqueries/'
        ),
        MSLearnModuleConfig(
            module_id='use-built-functions-transact-sql',
            title='Use built-in functions and GROUP BY in Transact-SQL',
            url='https://learn.microsoft.com/en-us/training/modules/use-built-functions-transact-sql/'
        ),
        MSLearnModuleConfig(
            module_id='modify-data-with-transact-sql',
            title='Modify data with T-SQL',
            url='https://learn.microsoft.com/en-us/training/modules/modify-data-with-transact-sql/'
        ),
    ]
)

# ASP.NET Core & Blazor: 3 verified modules with explicit knowledge-check units
ASPNET_COURSE = MSLearnCourseConfig(
    course_id='MSLEARN_ASPNET',
    display_name='MS Learn — ASP.NET Core & Blazor Web Development',
    modules=[
        MSLearnModuleConfig(
            module_id='introduction-to-aspnet-core',
            title='Introduction to .NET web development with ASP.NET Core',
            url='https://learn.microsoft.com/en-us/training/modules/introduction-to-aspnet-core/'
        ),
        MSLearnModuleConfig(
            module_id='build-your-first-aspnet-core-web-app',
            title='Build your first ASP.NET Core web app',
            url='https://learn.microsoft.com/en-us/training/modules/build-your-first-aspnet-core-web-app/'
        ),
        MSLearnModuleConfig(
            module_id='build-blazor-todo-list',
            title='Build a to-do list with Blazor',
            url='https://learn.microsoft.com/en-us/training/modules/build-blazor-todo-list/'
        ),
    ]
)

# ── Fullstack / Web Dev Priority List ────────────────────────────────────────
# Removed: NODEJS_COURSE (all 6 modules broken), REACT_COURSE (all broken),
#          TYPESCRIPT_COURSE (redirects to typescriptlang.org)
ALL_MSLEARN_COURSES = [
    # ── Core Web Dev ──────────────────────────────────────────────────────────
    WEB101_COURSE,            # 2 verified modules (accessibility, conditional)
    ASPNET_COURSE,            # ASP.NET Core & Blazor (3 modules)
    # ── GitHub Ecosystem ──────────────────────────────────────────────────────
    GITHUB_COURSE,            # Git & GitHub basics (4 modules)
    GITHUB_ADVANCED_COURSE,   # PRs, merge conflicts, open source (6 modules)
    GITHUB_ACTIONS_COURSE,    # CI/CD automation (5 modules)
    GITHUB_COPILOT_COURSE,    # AI pair programming (5 modules)
    # ── Scripting & Languages ─────────────────────────────────────────────────
    PYTHON_COURSE,            # 3 verified modules
    CSHARP_COURSE,            # 8 verified modules
    # ── Database ──────────────────────────────────────────────────────────────
    TSQL_COURSE,              # T-SQL fundamentals (6 modules)
    # ── Cloud & Data ──────────────────────────────────────────────────────────
    AZURE_FUNDAMENTALS_COURSE,       # AZ-900 (11 modules)
    AI_FUNDAMENTALS_COURSE,          # AI-900 (4 modules)
    POWERBI_COURSE,                  # 3 verified modules
    SECURITY_FUNDAMENTALS_COURSE,    # SC-900 (8 modules)
]
